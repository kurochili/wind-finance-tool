"""
wind_finance.smart_input
========================
从 Excel 或图片中智能提取风电项目参数
"""

import re
import io
from typing import List, Dict, Optional

import pandas as pd

# ---------------------------------------------------------------------------
# 关键字 → 输出字段的映射（正则模式, 大小写不敏感）
# ---------------------------------------------------------------------------
_FIELD_PATTERNS: List[tuple] = [
    (r"units?",                     "units"),
    (r"p90.*h.*y|p90",             "p90_hours"),
    (r"tariff|electricity\s*tariff","tariff_usd"),
    (r"\brna\b",                    "rna_per_kw"),
    (r"\btower\b",                  "tower_per_kw"),
    (r"transport",                  "transportation_per_kw"),
    (r"install",                    "installation_per_kw"),
    (r"\btsi\b",                    "tsi_per_kw"),
    (r"\bbop\b",                    "bop_per_kw"),
    (r"\bcapex\b",                  "capex_per_kw"),
    (r"\blcoe\b",                   "lcoe"),
]

_HEADER_KEYWORDS = re.compile(
    r"wtg|units?|p90|capex|tariff|rna|tower|bop|tsi|install|transport|lcoe",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# 辅助工具
# ---------------------------------------------------------------------------

def extract_mw_from_name(name: str) -> float:
    """从机型名称中提取额定功率 (MW)。

    规则：在 "MySE" 后面提取第一个数字串（可含小数点），
    如 MySE8.5-230 → 8.5, MySE10-242 → 10.0, MySE16.X-260 → 16.0
    """
    if not name:
        return 0.0
    m = re.search(r"MySE\s*(\d+\.?\d*)", name, re.IGNORECASE)
    if m:
        return float(m.group(1))
    # 退化：取字符串中第一个合理的数字
    m = re.search(r"(\d+\.?\d*)", name)
    if m:
        val = float(m.group(1))
        if val < 30:  # MW 不会超过 30
            return val
    return 0.0


def _parse_number(text: str) -> Optional[float]:
    """将单元格文本转为浮点数，处理逗号、百分号、空白等。"""
    if text is None:
        return None
    if isinstance(text, (int, float)):
        if pd.isna(text):
            return None
        return float(text)
    s = str(text).strip()
    if not s or s in ("-", "—", "–", "N/A", "n/a", ""):
        return None
    is_pct = "%" in s
    s = s.replace(",", "").replace("%", "").replace(" ", "")
    # 处理括号表示负数: (5.95) → -5.95
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg = True
        s = s[1:-1]
    try:
        val = float(s)
    except ValueError:
        return None
    if neg:
        val = -val
    if is_pct:
        val = val / 100.0
    return val


def _match_field(label: str) -> Optional[str]:
    """将表格行标题匹配到标准字段名。"""
    label_clean = str(label).strip()
    if re.search(r"wtg\s*type|机型|turbine", label_clean, re.IGNORECASE):
        return "wtg_type"
    for pattern, field_name in _FIELD_PATTERNS:
        if re.search(pattern, label_clean, re.IGNORECASE):
            return field_name
    return None


# ---------------------------------------------------------------------------
# 1. Excel 解析
# ---------------------------------------------------------------------------

def parse_excel(file_bytes: bytes) -> List[Dict]:
    """解析 Excel 文件，提取每列（每个机型方案）的参数。

    Parameters
    ----------
    file_bytes : bytes
        Excel 文件的二进制内容（.xlsx / .xls）

    Returns
    -------
    list[dict]
        每个机型方案对应一个字典
    """
    try:
        df = pd.read_excel(io.BytesIO(file_bytes), header=None, engine="openpyxl")
    except Exception:
        try:
            df = pd.read_excel(io.BytesIO(file_bytes), header=None)
        except Exception:
            return []

    # 寻找表头行：含有 WTG/Units/P90/CAPEX 等关键字的行
    header_row = _find_header_row(df)
    if header_row is None:
        return []

    # 确定数据列（排除第一列标签列）
    label_col = 0
    data_cols = [c for c in range(1, df.shape[1]) if not _is_empty_col(df, c, header_row)]
    if not data_cols:
        return []

    # 逐列提取
    results: List[Dict] = []
    for col_idx in data_cols:
        record: Dict = {}
        for row_idx in range(header_row, df.shape[0]):
            label = df.iloc[row_idx, label_col]
            field = _match_field(label)
            if field is None:
                continue
            raw_val = df.iloc[row_idx, col_idx]
            if field == "wtg_type":
                record["wtg_type"] = str(raw_val).strip() if pd.notna(raw_val) else ""
            else:
                num = _parse_number(raw_val)
                if num is not None:
                    record[field] = num

        if not record or "wtg_type" not in record:
            continue

        # 自动推断 MW
        record["turbine_mw"] = extract_mw_from_name(record.get("wtg_type", ""))
        results.append(record)

    return results


def _find_header_row(df: pd.DataFrame) -> Optional[int]:
    """在 DataFrame 中找到包含关键字最多的行作为表头起始行。"""
    best_row = None
    best_score = 0
    for row_idx in range(min(df.shape[0], 30)):  # 只搜索前 30 行
        score = 0
        for col_idx in range(df.shape[1]):
            cell = str(df.iloc[row_idx, col_idx])
            if _HEADER_KEYWORDS.search(cell):
                score += 1
        if score > best_score:
            best_score = score
            best_row = row_idx
    return best_row if best_score >= 1 else None


def _is_empty_col(df: pd.DataFrame, col: int, start_row: int) -> bool:
    """判断某列从 start_row 开始是否全部为空。"""
    for row_idx in range(start_row, min(df.shape[0], start_row + 20)):
        val = df.iloc[row_idx, col]
        if pd.notna(val) and str(val).strip():
            return False
    return True


# ---------------------------------------------------------------------------
# 2. 图片 OCR 解析
# ---------------------------------------------------------------------------

def parse_image(image_bytes: bytes) -> tuple:
    """用 OCR 从截图中提取风电项目参数。

    Returns
    -------
    tuple(list[dict], str, str)
        (方案列表, OCR原始文本, 错误信息)
        如果成功: (variants, ocr_text, "")
        如果失败: ([], "", error_message)
    """
    try:
        from PIL import Image
    except ImportError:
        return [], "", "Pillow 未安装，无法处理图片"

    try:
        import pytesseract
    except ImportError:
        return [], "", "pytesseract 未安装。请确认 packages.txt 包含 tesseract-ocr"

    try:
        img = Image.open(io.BytesIO(image_bytes))
    except Exception as e:
        return [], "", f"图片打开失败: {e}"

    try:
        text = pytesseract.image_to_string(img, lang="eng+chi_sim")
    except Exception as e:
        err_str = str(e)
        if "chi_sim" in err_str:
            try:
                text = pytesseract.image_to_string(img, lang="eng")
            except Exception as e2:
                return [], "", f"OCR 失败 (eng fallback): {e2}"
        else:
            return [], "", f"OCR 失败: {e}"

    if not text or not text.strip():
        return [], "", "OCR 未识别到任何文字。建议检查图片是否清晰、是否为截图格式。"

    variants = _parse_ocr_text(text)
    return variants, text, ""


def _parse_ocr_text(text: str) -> List[Dict]:
    """将 OCR 识别出的文本解析为结构化参数字典列表。"""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return []

    # 第一步：找到 WTG Type 行来确定有几列（几个方案）
    num_schemes = 0
    wtg_names: List[str] = []

    for line in lines:
        if re.search(r"wtg\s*type|机型|turbine", line, re.IGNORECASE):
            tokens = re.split(r"[|\t]{1,}|  {2,}", line)
            tokens = [t.strip() for t in tokens if t.strip()]
            # 排除标签本身
            for t in tokens:
                if re.search(r"MySE|WTG|机型|turbine", t, re.IGNORECASE):
                    if re.search(r"\d", t) and re.search(r"MySE", t, re.IGNORECASE):
                        wtg_names.append(t)
                elif re.search(r"\d", t):
                    wtg_names.append(t)
            break

    num_schemes = max(len(wtg_names), 1)
    if not wtg_names:
        # 尝试从所有行中猜测方案数
        num_schemes = _guess_num_schemes(lines)

    # 初始化记录
    records: List[Dict] = [{"wtg_type": wtg_names[i] if i < len(wtg_names) else ""}
                           for i in range(num_schemes)]

    # 逐行匹配关键字并提取数值
    for line in lines:
        field = _match_field(line)
        if field is None or field == "wtg_type":
            continue

        numbers = _extract_numbers_from_line(line)
        for i, num in enumerate(numbers):
            if i < num_schemes:
                records[i][field] = num

    # 填充 turbine_mw
    final: List[Dict] = []
    for rec in records:
        if len(rec) <= 1:
            continue
        rec["turbine_mw"] = extract_mw_from_name(rec.get("wtg_type", ""))
        final.append(rec)

    return final


def _guess_num_schemes(lines: List[str]) -> int:
    """根据数值列数量猜测方案数。"""
    counts = []
    for line in lines:
        nums = _extract_numbers_from_line(line)
        if nums:
            counts.append(len(nums))
    if not counts:
        return 1
    from collections import Counter
    most_common = Counter(counts).most_common(1)[0][0]
    return max(most_common, 1)


def _extract_numbers_from_line(line: str) -> List[float]:
    """从一行文本中提取所有数值。"""
    # 先按分隔符拆分
    tokens = re.split(r"[|\t]", line)
    if len(tokens) < 2:
        tokens = re.split(r"  {2,}", line)

    results = []
    for token in tokens:
        token = token.strip()
        num = _parse_number(token)
        if num is not None:
            results.append(num)
    return results


# ---------------------------------------------------------------------------
# 3. 国家/地区自动检测
# ---------------------------------------------------------------------------

_COUNTRY_KEYWORDS: Dict[str, List[str]] = {
    "Vietnam":      ["vietnam", "viet nam", "越南", "vnđ", "vnd", "ha tinh", "hà tĩnh",
                     "soc trang", "sóc trăng", "binh thuan", "bình thuận", "quang tri",
                     "quảng trị", "decision 1508", "qđ-bct", "nearshore"],
    "Philippines":  ["philippines", "菲律宾", "php", "laguna", "luzon", "visayas",
                     "mindanao", "doe", "feed-in tariff"],
    "China":        ["china", "中国", "cny", "rmb", "人民币", "广东", "江苏", "浙江",
                     "山东", "福建", "上海", "guangdong", "jiangsu", "zhejiang",
                     "shandong", "fujian", "海上风电"],
    "Thailand":     ["thailand", "泰国", "thb", "baht", "กรุงเทพ"],
    "Indonesia":    ["indonesia", "印尼", "印度尼西亚", "idr", "rupiah", "java", "sulawesi",
                     "sumatra", "kalimantan"],
    "Malaysia":     ["malaysia", "马来西亚", "myr", "ringgit", "sabah", "sarawak"],
    "Cambodia":     ["cambodia", "柬埔寨", "khr", "riel", "phnom penh"],
    "Japan":        ["japan", "日本", "jpy", "yen", "円", "hokkaido", "北海道",
                     "秋田", "akita", "千葉", "chiba"],
    "South Korea":  ["korea", "韩国", "krw", "won", "원", "jeju", "전남", "전북"],
    "Australia":    ["australia", "澳大利亚", "澳洲", "aud", "nsw", "victoria",
                     "queensland", "south australia"],
    "Taiwan":       ["taiwan", "台湾", "twd", "彰化", "changhua", "竹南",
                     "zhunan", "苗栗", "miaoli"],
}


def detect_country(text: str, filename: str = "") -> Optional[str]:
    """从文本内容和文件名中推断国家/地区。

    Parameters
    ----------
    text : str
        Excel 原始文本 / OCR 文本 / 所有单元格拼接文本
    filename : str
        上传的文件名

    Returns
    -------
    str or None
        匹配到的国家英文名（与 country_profiles 中一致），未命中则 None
    """
    combined = (filename + " " + text).lower()
    scores: Dict[str, int] = {}
    for country, keywords in _COUNTRY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in combined)
        if score > 0:
            scores[country] = score
    if not scores:
        return None
    return max(scores, key=scores.get)


def detect_country_from_excel(file_bytes: bytes, filename: str = "") -> Optional[str]:
    """从 Excel 文件中提取全部文本进行国家检测。"""
    try:
        df = pd.read_excel(io.BytesIO(file_bytes), header=None, engine="openpyxl")
    except Exception:
        try:
            df = pd.read_excel(io.BytesIO(file_bytes), header=None)
        except Exception:
            return detect_country("", filename)
    all_text = " ".join(str(v) for v in df.values.flatten() if pd.notna(v))
    return detect_country(all_text, filename)


def detect_country_from_image_text(ocr_text: str, filename: str = "") -> Optional[str]:
    """从 OCR 文本中检测国家。"""
    return detect_country(ocr_text, filename)
