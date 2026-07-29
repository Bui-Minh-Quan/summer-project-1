"""
Versioned prompt templates and registry for Target-Anchored TRR Knowledge Graph Extraction.
Focused exclusively on a 10-Stock Target Portfolio with Anti-Super Node defenses.
"""

from dataclasses import dataclass
from typing import ClassVar

# =====================================================================
# TARGET PORTFOLIO DICTIONARY (10 Core VN30 Equities)
# =====================================================================

TARGET_PORTFOLIO: dict[str, list[str]] = {
    "FPT": ["CTCP FPT", "Tập đoàn FPT", "FPT Telecom", "FPT Software"],
    "SSI": ["CTCP Chứng khoán SSI", "Chứng khoán SSI", "SSI Securities"],
    "VCB": ["Ngân hàng TMCP Ngoại thương Việt Nam", "Ngân hàng Vietcombank", "Vietcombank"],
    "VHM": ["CTCP Vinhomes", "Tập đoàn Vinhomes", "Vinhomes"],
    "HPG": ["CTCP Tập đoàn Hòa Phát", "Tập đoàn Hòa Phát", "Thép Hòa Phát", "Hòa Phát"],
    "GAS": ["Tổng Công ty Khí Việt Nam", "PV GAS", "Khí Việt Nam"],
    "MSN": ["CTCP Tập đoàn Masan", "Tập đoàn Masan", "Masan Group", "Masan"],
    "MWG": ["CTCP Đầu tư Thế Giới Di Động", "Thế Giới Di Động", "Mobile World Group", "Điện máy Xanh"],
    "GVR": ["Tập đoàn Công nghiệp Cao su Việt Nam", "Cao su Việt Nam", "VRG"],
    "VIC": ["CTCP Tập đoàn Vingroup", "Tập đoàn Vingroup", "Vingroup"],
}


VN30_ALIAS_MAP: dict[str, list[str]] = {
    "ACB": ["Ngân hàng TMCP Á Châu", "Ngân hàng ACB", "Á Châu", "ACB Bank"],
    "BID": ["Ngân hàng TMCP Đầu tư và Phát triển Việt Nam", "Ngân hàng BIDV", "BIDV"],
    "CTG": ["Ngân hàng TMCP Công Thương Việt Nam", "Ngân hàng VietinBank", "VietinBank"],
    "DGC": ["CTCP Tập đoàn Hóa chất Đức Giang", "Hóa chất Đức Giang", "Tập đoàn Hóa chất Đức Giang", "Đức Giang"],
    "FPT": ["CTCP FPT", "Tập đoàn FPT", "FPT Telecom", "FPT Software", "FPT Retail"],
    "GAS": ["Tổng Công ty Khí Việt Nam", "PV GAS", "Khí Việt Nam"],
    "GVR": ["Tập đoàn Công nghiệp Cao su Việt Nam", "Cao su Việt Nam", "VRG"],
    "HDB": ["Ngân hàng TMCP Phát triển TP.HCM", "Ngân hàng HDBank", "HDBank"],
    "HPG": ["CTCP Tập đoàn Hòa Phát", "Tập đoàn Hòa Phát", "Thép Hòa Phát", "Hòa Phát"],
    "LPB": ["Ngân hàng TMCP Lộc Phát Việt Nam", "Ngân hàng LPBank", "LPBank", "Liên Việt"],
    "MBB": ["Ngân hàng TMCP Quân Đội", "Ngân hàng MB", "MBBank", "MB"],
    "MSN": ["CTCP Tập đoàn Masan", "Tập đoàn Masan", "Masan Group", "Masan"],
    "MWG": ["CTCP Đầu tư Thế Giới Di Động", "Thế Giới Di Động", "Mobile World Group", "Điện máy Xanh"],
    "PLX": ["Tập đoàn Xăng dầu Việt Nam", "Petrolimex", "Xăng dầu Việt Nam"],
    "SAB": ["Tổng Công ty Cổ phần Bia - Rượu - Nước giải khát Sài Gòn", "Sabeco", "Bia Sài Gòn"],
    "SHB": ["Ngân hàng TMCP Sài Gòn - Hà Nội", "Ngân hàng SHB", "SHB Bank"],
    "SSB": ["Ngân hàng TMCP Đông Nam Á", "Ngân hàng SeABank", "SeABank"],
    "SSI": ["CTCP Chứng khoán SSI", "Chứng khoán SSI", "SSI Securities"],
    "STB": ["Ngân hàng TMCP Sài Gòn Thương Tín", "Ngân hàng Sacombank", "Sacombank"],
    "TCB": ["Ngân hàng TMCP Kỹ Thương Việt Nam", "Ngân hàng Techcombank", "Techcombank"],
    "TPB": ["Ngân hàng TMCP Tiên Phong", "Ngân hàng TPBank", "TPBank", "Tiên Phong Bank"],
    "VCB": ["Ngân hàng TMCP Ngoại thương Việt Nam", "Ngân hàng Vietcombank", "Vietcombank"],
    "VHM": ["CTCP Vinhomes", "Tập đoàn Vinhomes", "Vinhomes"],
    "VIB": ["Ngân hàng TMCP Quốc tế Việt Nam", "Ngân hàng VIB", "VIB Bank", "Ngân hàng Quốc tế"],
    "VIC": ["CTCP Tập đoàn Vingroup", "Tập đoàn Vingroup", "Vingroup"],
    "VJC": ["CTCP Hàng không Vietjet", "Vietjet Air", "Hàng không Vietjet", "Vietjet"],
    "VNM": ["CTCP Sữa Việt Nam", "Vinamilk", "Sữa Việt Nam"],
    "VPB": ["Ngân hàng TMCP Việt Nam Thịnh Vượng", "Ngân hàng VPBank", "VPBank"],
    "VPL": ["CTCP Vinpearl", "Tập đoàn Vinpearl", "Vinpearl"],
    "VRE": ["CTCP Vincom Retail", "Vincom Retail", "Vincom"],
}


# =====================================================================
# SYSTEM & USER PROMPTS (Target-Anchored Architecture)
# =====================================================================

SYSTEM_PROMPT_TRR_TARGETED_V1 = """Bạn là một chuyên gia phân tích kinh tế vĩ mô và chiến lược thị trường chứng khoán Việt Nam.
Nhiệm vụ của bạn là xây dựng Đồ thị Tri thức (Knowledge Graph) tập trung tối đa vào chuỗi tác động đến DANH MỤC CỔ PHIẾU TRỌNG TÂM.

1. DANH MỤC CỔ PHIẾU ƯU TIÊN (TARGET PORTFOLIO):
{portfolio_block}

QUY TẮC BẮT BUỘC TUÂN THỦ:

Quy tắc 1: QUY ĐỊNH KHI NÀO TRẢ VỀ DANH SÁCH RỖNG `{"relations": []}` (RẤT QUAN TRỌNG)
Bạn BẮT BUỘC phải trả về danh sách rỗng `{"relations": []}` nếu bài viết rơi vào một trong các trường hợp sau:
- Bài viết về đời sống, thủ tục hành chính dân sự, trật tự xã hội, sinh hoạt (Ví dụ: cấp đổi sổ đỏ, đăng ký đất đai, phạt tiền điện nhà trọ, sự cố mạng viễn thông dân sự...).
- Bài viết không đề cập trực tiếp hoặc gián tiếp đến bất kỳ cổ phiếu nào trong DANH MỤC CỔ PHIẾU ƯU TIÊN, cũng không ảnh hưởng đến các NGÀNH hay BIẾN SỐ VĨ MÔ liên quan.
- Thông tin quá chung chung và toàn bộ thực thể trích xuất ra đều bị cấm bởi Quy tắc 4 (Anti-Super Nodes).

Quy tắc 2: ĐỊNH DANH CỔ PHIẾU
- Nếu thực thể là doanh nghiệp nằm trong DANH MỤC CỔ PHIẾU ƯU TIÊN, bạn BẮT BUỘC dùng MÃ CỔ PHIẾU 3 CHỮ CÁI làm tên thực thể (`name`) và gán `entity_type: "STOCK"`.
- TUYỆT ĐỐI KHÔNG dùng tên đầy đủ hay tên tiếng Việt cho các mã này.
  ❌ Ví dụ sai: "Tập đoàn Hòa Phát", "Cổ phiếu HPG", "HPG Steel", "Vinamilk".
  ✅ Ví dụ đúng: "HPG", "VCB", "FPT", "VIC".

Quy tắc 3: PHÂN LOẠI LOẠI THỰC THỂ (ENTITY_TYPE)
Mỗi thực thể (`subject` và `object`) bắt buộc phải gán chính xác 1 trong 7 loại sau:
- `ORGANIZATION`: Doanh nghiệp, ngân hàng, cơ quan nhà nước, quỹ đầu tư, tổ chức. (Lưu ý: Nếu doanh nghiệp thuộc TARGET PORTFOLIO, ưu tiên dùng mã `STOCK` theo Quy tắc 2).
- `STOCK`: Mã chứng khoán niêm yết chính thức (Ví dụ: "HPG", "VCB", "FPT", "SSI").
- `SECTOR`: Lĩnh vực hoặc ngành kinh tế chung (Ví dụ: "Ngành Ngân hàng", "Ngành Bất động sản", "Ngành Thép").
- `PERSON`: Cá nhân cụ thể có tên riêng (Ví dụ: "Trần Đình Long", "Jerome Powell").
- `COMMODITY`: Hàng hóa, nguyên nhiên vật liệu (Ví dụ: "Giá cao su tự nhiên", "Thép cuộn", "Dầu Brent").
- `INDEX`: Chỉ số thị trường chứng khoán (Ví dụ: "VN-Index", "VN30").
- `OTHER`: Biến số vĩ mô, chỉ tiêu tài chính, chính sách, khái niệm kinh tế (Ví dụ: "Lãi suất cho vay", "GDP", "Tỷ giá USD/VND").

Quy tắc 4: CẤM SỬ DỤNG TỪ KHÓA CHUNG CHUNG (ANTI-SUPER NODES)
- Bạn TUYỆT ĐỐI KHÔNG được tạo ra các node có tên sau đây:
  ["Doanh nghiệp", "Công ty", "Nhà đầu tư", "Người dân", "Thị trường", "Kinh tế", "Việt Nam", "Chính phủ", "Nhà nước", "Khách hàng", "Người lao động", "Xã hội"].
- Thay vào đó, bạn PHẢI cụ thể hóa chúng:
  ❌ "Doanh nghiệp" -> ✅ "Doanh nghiệp Xuất khẩu thủy sản", "Doanh nghiệp BĐS", "SME".
  ❌ "Nhà đầu tư"   -> ✅ "Khối ngoại", "Tự doanh", "Nhà đầu tư cá nhân".
  ❌ "Người dân"    -> ✅ "Người mua nhà", "Tầng lớp thu nhập thấp".
  ❌ "Nhà nước"     -> ✅ "Ngân hàng Nhà nước", "Bộ Tài chính".
- Nếu không thể cụ thể hóa -> BẮT BUỘC BỎ QUA, không trích xuất.

Quy tắc 5: PHÂN TÍCH TÁC ĐỘNG & SỐ LƯỢNG
- Chỉ trích xuất TỐI ĐA 4 liên kết quan trọng nhất chịu ảnh hưởng trực tiếp.
- Luôn viết câu giải thích `reasoning` đầu tiên, ngắn gọn, chứa từ khóa kinh tế. Nếu có số liệu (tăng 5%, lãi 1000 tỷ...), phải đưa vào `reasoning`.
- `market_impact`: POSITIVE (Có lợi/Tăng giá), NEGATIVE (Gây hại/Giảm giá), NEUTRAL (Trung lập/Cấu trúc).

Quy tắc 6: ƯU TIÊN NGÀNH VÀ HÀNG HÓA (CAUSAL BRIDGING)
- Nếu bài viết nói về biến số vĩ mô không nhắc trực tiếp mã cổ phiếu, hãy kết nối biến số vĩ mô (`OTHER`/`COMMODITY`) với NGÀNH (`SECTOR`) liên quan.

---
VÍ DỤ MINH HỌA (CHỈ CHỨA GIÁ TRỊ GIẢ ĐỊNH ĐỂ MINH HỌA CẤU TRÚC JSON - TUYỆT ĐỐI KHÔNG DÙNG LẠI CÁC KÝ HIỆU HÀNG HÓA, MÃ AAA, CƠ QUAN Y HAY NGÀNH W DƯỚI ĐÂY VÀO BÀI BÁO THẬT):

Ví dụ 1 (Tác động từ hàng hóa lên mã cổ phiếu giả định AAA):
Đầu vào:
"Hàng hóa X tăng giá 10% giúp nâng cao biên lợi nhuận của Công ty Alpha (Mã AAA)."
Đầu ra:
{
  "relations": [
    {
      "reasoning": "Hàng hóa X tăng giá 10% làm tăng giá bán đầu ra, giúp nâng cao biên lợi nhuận của AAA.",
      "subject": {
        "name": "Hàng hóa X",
        "entity_type": "COMMODITY"
      },
      "relation": "tăng giá 10% giúp nâng cao biên lợi nhuận",
      "object": {
        "name": "AAA",
        "entity_type": "STOCK"
      },
      "market_impact": "POSITIVE",
      "confidence": 0.99
    }
  ]
}

Ví dụ 2 (Cầu nối giữa cơ quan quản lý và ngành kinh tế giả định W):
Đầu vào:
"Cơ quan Y tăng chỉ số Z tạo sức ép lớn lên chi phí hoạt động của các doanh nghiệp thuộc Ngành W."
Đầu ra:
{
  "relations": [
    {
      "reasoning": "Cơ quan Y tăng chỉ số Z làm gia tăng chi phí hoạt động của các doanh nghiệp thuộc Ngành W.",
      "subject": {
        "name": "Cơ quan Y",
        "entity_type": "ORGANIZATION"
      },
      "relation": "tăng chỉ số Z làm tăng chi phí hoạt động",
      "object": {
        "name": "Ngành W",
        "entity_type": "SECTOR"
      },
      "market_impact": "NEGATIVE",
      "confidence": 0.95
    }
  ]
}

Ví dụ 3 (Tin tức hành chính / dân sự không liên quan đến tài chính):
Đầu vào:
"Cơ quan địa phương triển khai chiến dịch làm sạch cảnh quan công cộng và cải tạo vỉa hè."
Đầu ra:
{
  "relations": []
}
"""

USER_PROMPT_TRR_TARGETED_V1 = """Tiêu đề: {title}

Nội dung:
{content}

---
{context_block}
---

Hãy trích xuất danh sách các quan hệ tác động (relations) dưới dạng JSON:"""


@dataclass(frozen=True)
class PromptTemplate:
    system_prompt: str
    user_prompt: str


class ExtractionPromptManager:
    """Registry pattern managing immutable Target-Anchored TRR prompt versions."""
    
    DEFAULT_VERSION: ClassVar[str] = "v1.0"
    
    _REGISTRY: ClassVar[dict[str, PromptTemplate]] = {
        "v1.0": PromptTemplate(
            system_prompt=SYSTEM_PROMPT_TRR_TARGETED_V1, 
            user_prompt=USER_PROMPT_TRR_TARGETED_V1
        ),
    }

    @classmethod
    def format_portfolio_block(cls, symbols: list[str] | None) -> str:
        """
        Formats the 10-stock Target Portfolio block. 
        If article metadata tags specific target stocks, highlights them as Priority 1 
        while keeping the remaining target universe visible for macro contagion.
        """
        tagged_targets = [
            s.strip().upper() for s in (symbols or [])
            if isinstance(s, str) and s.strip().upper() in TARGET_PORTFOLIO
        ]
        
        # Deduplicate while preserving sequence
        priority_tickers = list(dict.fromkeys(tagged_targets))
        seen = set(priority_tickers)
        other_tickers = [x for x in TARGET_PORTFOLIO if x not in seen]
        
        lines = []
        if priority_tickers:
            lines.append("🔥 CỔ PHIẾU TRỌNG TÂM ĐƯỢC NHẮC TRỰC TIẾP TRONG BÀI (ƯU TIÊN SỐ 1):")
            for ticker in priority_tickers:
                aliases = ", ".join(TARGET_PORTFOLIO[ticker])
                lines.append(f"  + Mã STOCK: \"{ticker}\" | Tên doanh nghiệp: {aliases}")
            lines.append("\n📌 CÁC CỔ PHIẾU KHÁC TRONG DANH MỤC (TÌM TÁC ĐỘNG GIÁN TIẾP NẾU CÓ):")
        else:
            lines.append("📌 DANH MỤC 10 CỔ PHIẾU TRỌNG TÂM CỦA HỆ THỐNG:")
            
        for ticker in other_tickers:
            aliases = ", ".join(TARGET_PORTFOLIO[ticker])
            lines.append(f"  + Mã STOCK: \"{ticker}\" | Tên doanh nghiệp: {aliases}")
            
        return "\n".join(lines)

    @classmethod
    def get_prompt(
        cls, 
        title: str, 
        content: str, 
        context_block: str, 
        symbols: list[str] | None = None,
        version: str = DEFAULT_VERSION
    ) -> tuple[str, str]:
        """Returns the dynamically formatted (system_prompt, user_prompt) tuple."""
        template = cls._REGISTRY.get(version)
        if not template:
            raise ValueError(f"Prompt version '{version}' not found.")
        
        portfolio_block = cls.format_portfolio_block(symbols)
        formatted_system = template.system_prompt.replace("{portfolio_block}", portfolio_block)
        
        formatted_user = (
            template.user_prompt
            .replace("{title}", title)
            .replace("{content}", content)
            .replace("{context_block}", context_block)
        )
        
        return formatted_system, formatted_user