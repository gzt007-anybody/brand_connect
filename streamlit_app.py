import base64
import json
from datetime import datetime

import streamlit as st
from openai import OpenAI


st.set_page_config(
    page_title="브랜드 포스트 스튜디오",
    page_icon="✦",
    layout="wide",
)

st.markdown(
    """
    <style>
    :root { --ink:#13261c; --green:#03c75a; --mint:#eafbf1; --line:#dce9e1; }
    .stApp { background: linear-gradient(135deg,#f7fbf8 0%,#ffffff 58%,#effbf4 100%); }
    .block-container { max-width: 1240px; padding-top: 1.6rem; }
    h1,h2,h3 { color:var(--ink); letter-spacing:-.035em; }
    div[data-testid="stMetric"] { background:white; border:1px solid var(--line); border-radius:16px; padding:12px 16px; }
    div[data-testid="stForm"] { background:rgba(255,255,255,.9); border:1px solid var(--line); border-radius:22px; padding:22px; box-shadow:0 16px 44px rgba(16,70,41,.06); }
    .notice { background:var(--mint); border-left:4px solid var(--green); padding:14px 16px; border-radius:10px; color:#244b35; }
    .eyebrow { color:#087a3d; font-size:.8rem; font-weight:800; letter-spacing:.1em; }
    </style>
    """,
    unsafe_allow_html=True,
)


def secret(name: str, default: str = "") -> str:
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


def money(value) -> str:
    try:
        return f"{int(float(value)):,}원"
    except (TypeError, ValueError):
        return "가격 미입력"


def build_source(product, competitors):
    lines = [
        f"상품명: {product['name']}",
        f"브랜드: {product['brand']}",
        f"카테고리: {product['category']}",
        f"판매가: {money(product['price'])}",
        f"제휴 링크: {product['affiliate_url']}",
        f"핵심 특징: {product['features']}",
        f"실제 사용/확인한 내용: {product['experience'] or '없음'}",
        f"주의점/단점: {product['cautions'] or '미입력'}",
        "경쟁상품:",
    ]
    for row in competitors:
        if row.get("상품명"):
            lines.append(
                f"- {row.get('상품명')}: {money(row.get('가격'))}, "
                f"장점={row.get('장점','')}, 아쉬운 점={row.get('아쉬운 점','')}"
            )
    return "\n".join(lines)


def generate_article(client, product, competitors, settings):
    source = build_source(product, competitors)
    disclosure = (
        "이 글에는 브랜드 커넥트 제휴 링크가 포함되어 있으며, "
        "링크를 통한 구매 시 작성자에게 수수료가 지급될 수 있습니다."
    )
    prompt = f"""
당신은 한국어 네이버 블로그의 정직한 상품 비교 에디터다.
아래 제공 자료만 사실로 사용하고, 확인하지 않은 사용 경험·효능·최저가를 만들지 마라.
가격은 변동될 수 있다고 명시하고, 과장된 확정 표현과 경쟁사 비방을 피하라.

[제공 자료]
{source}

[작성 조건]
- 독자: {settings['audience']}
- 문체: {settings['tone']}
- 목표 분량: 약 {settings['length']}자
- 핵심 키워드: {settings['keywords'] or product['name']}
- 첫 문단 전에 다음 문구를 그대로 표시: {disclosure}
- 제목 후보 5개, 한줄 요약, 본문, 비교표, 추천 대상/비추천 대상, 구매 전 확인사항, 해시태그 순서
- 링크는 본문 후반의 자연스러운 행동 문구 한 곳에만 넣기
- 실제 경험이 비어 있으면 체험한 것처럼 1인칭으로 쓰지 않기
- Markdown으로 작성
"""
    response = client.responses.create(
        model=secret("TEXT_MODEL", "gpt-5.6-luna"),
        input=prompt,
    )
    return response.output_text


def build_image_prompt(product, style, comment, image_number, has_references=False):
    reference_rule = (
        "첨부된 원본 상품 이미지의 형태·색상·패턴·주요 디테일을 우선 보존하고, "
        "배경과 연출만 사용자의 요청에 맞게 바꾸세요."
        if has_references
        else "원본 이미지가 없으므로 실제 상품의 정확한 외형을 아는 것처럼 만들지 말고 일반적인 연출 이미지로 표현하세요."
    )
    return f"""
한국어 커머스 블로그에 사용할 {image_number}번 이미지를 생성하세요.
상품명: {product['brand']} {product['name']}
공식 자료에서 확인된 특징: {product['features']}
공통 분위기: {style}
사용자가 원하는 장면과 방향: {comment}
원본 이미지 사용 지침: {reference_rule}

자연스러운 조명과 깔끔한 에디토리얼 구도를 사용하세요. 가로형 블로그 이미지로 만들고,
확인되지 않은 로고·문구·가격·인증 배지·효능을 넣지 마세요. 실제 상품의 정확한 외형을
알 수 없는 부분은 임의로 단정하지 말고 일반적인 연출 이미지로 표현하세요. 이미지 안에
글자를 넣지 말고, 다른 이미지와 구도 및 장면이 겹치지 않게 만드세요.
""".strip()


def generate_image(client, product, style, comment, image_number, reference_images=None):
    reference_images = reference_images or []
    prompt = build_image_prompt(product, style, comment, image_number, bool(reference_images))
    response_input = prompt
    if reference_images:
        content = [{"type": "input_text", "text": prompt}]
        for image_bytes, mime_type in reference_images:
            encoded = base64.b64encode(image_bytes).decode("utf-8")
            content.append(
                {
                    "type": "input_image",
                    "image_url": f"data:{mime_type};base64,{encoded}",
                    "detail": "auto",
                }
            )
        response_input = [{"role": "user", "content": content}]
    response = client.responses.create(
        model=secret("IMAGE_ORCHESTRATOR_MODEL", "gpt-5.5"),
        input=response_input,
        tools=[
            {
                "type": "image_generation",
                "model": secret("IMAGE_MODEL", "gpt-image-2.5-flare"),
                "size": "1536x1024",
                "action": "generate",
            }
        ],
        tool_choice={"type": "image_generation"},
    )
    for item in response.output:
        if getattr(item, "type", "") == "image_generation_call":
            return base64.b64decode(item.result), getattr(item, "revised_prompt", prompt), prompt
    raise RuntimeError("이미지 결과를 받지 못했습니다.")


COMIC_STYLES = {
    "따뜻한 생활툰": "따뜻한 파스텔 색감, 친근한 생활 웹툰, 부드러운 선과 표정",
    "신문 연재 만화": "간결한 펜선, 절제된 색, 재치 있는 신문 연재 4컷 만화",
    "깔끔한 컬러 웹툰": "선명한 컬러, 깨끗한 윤곽선, 현대적인 한국 웹툰",
}


def _json_from_text(text):
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
    return json.loads(cleaned.strip())


def generate_galmel_story(client, product, article, tone, direction):
    prompt = f"""
당신은 정직한 한국어 커머스 4컷 만화 작가다. 고정 주인공 이름은 '갈멜'이다.
갈멜은 친근하고 현실적인 한국 중년 남성이며, 단순한 표정과 몸짓으로 생활 속 구매 고민을 유머 있게 보여준다.

[상품 자료]
{build_source(product, [])}

[블로그 초안]
{article[:7000]}

[요청]
- 분위기: {tone}
- 사용자의 추가 방향: {direction or '없음'}
- 흐름은 1) 생활 속 고민 2) 비교하며 생긴 웃긴 상황 3) 제공된 사실에 근거한 상품 발견 4) 자신에게 맞는지 확인하고 링크를 살펴보는 합리적 선택으로 구성한다.
- 구매 관심은 자연스럽게 높이되 허위 할인, 품절 압박, 공포·죄책감, 가짜 후기, 보장되지 않은 효과를 쓰지 않는다.
- 상품의 단점이나 확인사항도 필요하면 짧게 반영한다.
- 이미지 안에서 읽히도록 대사는 패널당 18자 안팎으로 짧게 쓴다.
- 오직 아래 구조의 유효한 JSON만 출력한다. 마크다운 코드블록은 쓰지 않는다.
{{
  "title": "짧은 만화 제목",
  "theme": "한 줄 주제",
  "panels": [
    {{"caption":"1컷", "scene":"그림 장면", "dialogue":"짧은 대사", "narration":"짧은 설명"}},
    {{"caption":"2컷", "scene":"그림 장면", "dialogue":"짧은 대사", "narration":"짧은 설명"}},
    {{"caption":"3컷", "scene":"그림 장면", "dialogue":"짧은 대사", "narration":"짧은 설명"}},
    {{"caption":"4컷", "scene":"그림 장면", "dialogue":"짧은 대사", "narration":"짧은 설명"}}
  ],
  "closing": "과장 없는 짧은 마무리 문구"
}}
"""
    response = client.responses.create(model=secret("TEXT_MODEL", "gpt-5.6-luna"), input=prompt)
    story = _json_from_text(response.output_text)
    if len(story.get("panels", [])) != 4:
        raise ValueError("4개 패널로 된 스토리를 받지 못했습니다.")
    return story


def galmel_story_text(story):
    lines = [f"# {story.get('title', '갈멜의 상품 고민')}", story.get("theme", ""), ""]
    for index, panel in enumerate(story.get("panels", []), 1):
        lines.extend([f"## {index}컷", f"장면: {panel.get('scene', '')}", f"갈멜: {panel.get('dialogue', '')}", f"설명: {panel.get('narration', '')}", ""])
    lines.append(f"마무리: {story.get('closing', '')}")
    return "\n".join(lines)


def build_galmel_comic_prompt(story, style):
    panels = []
    for index, panel in enumerate(story.get("panels", []), 1):
        panels.append(f"{index}컷 장면: {panel.get('scene', '')}\n말풍선: {panel.get('dialogue', '')}\n하단 설명: {panel.get('narration', '')}")
    return f"""
제목 '{story.get('title', '갈멜의 상품 고민')}'의 한국어 4컷 만화를 한 장에 그리세요.
주인공은 모든 칸에서 동일한 얼굴과 옷을 유지하는 고정 캐릭터 '갈멜'입니다.
갈멜은 친근한 한국 중년 남성이고 과장되지 않은 표정과 몸짓으로 현실적인 유머를 보여줍니다.
화풍: {COMIC_STYLES[style]}
가로 2x2 배열, 칸 경계가 명확하고 읽는 순서는 왼쪽 위부터 오른쪽 아래입니다.

{chr(10).join(panels)}

한국어 문구는 위에 지정된 짧은 문구만 정확하고 크게 표시하세요. 확인되지 않은 로고·가격·할인율·효능은 넣지 마세요.
제품 외형을 정확히 알 수 없는 부분은 일반적인 소품으로 단순화하세요. 마지막 장면은 강압적인 구매가 아니라
'나에게 맞는지 확인해 보자'는 기분 좋은 여운을 주세요.
""".strip()


def generate_galmel_comic(client, story, style):
    prompt = build_galmel_comic_prompt(story, style)
    result = client.images.generate(model=secret("IMAGE_MODEL", "gpt-image-2.5-flare"), prompt=prompt, size="1536x1024", quality="medium")
    encoded = result.data[0].b64_json
    if not encoded:
        raise RuntimeError("만화 이미지 결과를 받지 못했습니다.")
    return base64.b64decode(encoded), prompt


st.markdown('<div class="eyebrow">BRAND POST STUDIO</div>', unsafe_allow_html=True)
st.title("상품 하나로, 설득력 있는 블로그 초안까지")
st.caption("상품 정보와 비교 대상을 입력하면 가격 비교표·블로그 원고·대표 이미지를 만듭니다.")

api_key = secret("OPENAI_API_KEY")
if not api_key:
    st.markdown(
        '<div class="notice"><b>설정이 한 번 필요합니다.</b> '
        '온라인 배포 설정의 Secrets에 OPENAI_API_KEY를 등록하면 글과 이미지 생성 버튼이 활성화됩니다.</div>',
        unsafe_allow_html=True,
    )

with st.form("product_form"):
    st.subheader("1. 소개할 상품")
    c1, c2, c3 = st.columns([1.4, 1, 1])
    name = c1.text_input("상품명 *", placeholder="예: 초경량 무선 청소기 A100")
    brand = c2.text_input("브랜드", placeholder="예: 브랜드명")
    category = c3.text_input("카테고리", placeholder="예: 생활가전")

    p1, p2 = st.columns([1, 2])
    price = p1.number_input("현재 판매가(원)", min_value=0, step=1000)
    affiliate_url = p2.text_input("브랜드커넥트 제휴 링크", placeholder="https://...")

    features = st.text_area(
        "공식 페이지에서 확인한 특징 *",
        placeholder="무게, 크기, 구성품, 소재, 보증기간 등 사실만 적어주세요.",
        height=100,
    )
    e1, e2 = st.columns(2)
    experience = e1.text_area(
        "직접 사용해 확인한 점",
        placeholder="사용하지 않았다면 비워두세요. AI가 체험담을 만들지 않습니다.",
        height=110,
    )
    cautions = e2.text_area(
        "주의점 또는 아쉬운 점",
        placeholder="배송비, 호환성, 옵션 차이, 가격 변동 등",
        height=110,
    )

    st.subheader("2. 비교할 상품")
    competitors = st.data_editor(
        [
            {"상품명": "", "가격": 0, "장점": "", "아쉬운 점": ""},
            {"상품명": "", "가격": 0, "장점": "", "아쉬운 점": ""},
        ],
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("3. 글의 방향")
    s1, s2, s3 = st.columns(3)
    audience = s1.text_input("주요 독자", value="구매를 고민하는 실용적인 소비자")
    tone = s2.selectbox("문체", ["친근하지만 객관적으로", "전문적이고 간결하게", "생활 밀착형 후기처럼"])
    length = s3.select_slider("목표 분량", options=[1200, 1800, 2400, 3000], value=1800)
    keywords = st.text_input("넣고 싶은 핵심 키워드", placeholder="쉼표로 구분, 과도한 반복은 피합니다")
    image_style = st.selectbox(
        "이미지 분위기",
        ["밝은 자연광의 미니멀 제품 사진", "차분한 프리미엄 에디토리얼", "생활 공간에서 자연스럽게 사용하는 장면"],
    )

    submitted = st.form_submit_button("초안 만들기", type="primary", use_container_width=True)

if submitted:
    if not name or not features:
        st.error("상품명과 확인된 특징을 입력해주세요.")
    elif not api_key:
        st.error("배포 설정에 OPENAI_API_KEY를 먼저 등록해주세요.")
    else:
        client = OpenAI(api_key=api_key)
        product = {
            "name": name,
            "brand": brand,
            "category": category,
            "price": price,
            "affiliate_url": affiliate_url,
            "features": features,
            "experience": experience,
            "cautions": cautions,
        }
        settings = {
            "audience": audience,
            "tone": tone,
            "length": length,
            "keywords": keywords,
        }
        st.session_state["product"] = product
        st.session_state["image_style"] = image_style
        st.session_state["generated_images"] = {}
        st.session_state.pop("galmel_story", None)
        st.session_state.pop("galmel_image", None)
        st.session_state["galmel_edit_version"] = 0
        for index in range(1, 5):
            st.session_state.pop(f"image_comment_{index}", None)
        try:
            with st.spinner("자료를 정리해 블로그 초안을 작성하고 있습니다..."):
                st.session_state["article"] = generate_article(client, product, competitors, settings)
            st.success("초안이 완성되었습니다. 사실관계와 가격을 꼭 확인해주세요.")
        except Exception as exc:
            st.error(f"글 생성 중 문제가 발생했습니다: {exc}")

if st.session_state.get("article"):
    st.divider()
    article_tab, image_tab, comic_tab, check_tab = st.tabs(["블로그 초안", "이미지 3~4장", "갈멜 4컷", "발행 전 점검"])
    with article_tab:
        st.markdown(st.session_state["article"])
        filename = f"blog_draft_{datetime.now():%Y%m%d_%H%M}.md"
        st.download_button(
            "Markdown 파일로 저장",
            st.session_state["article"],
            file_name=filename,
            mime="text/markdown",
            use_container_width=True,
        )
    with image_tab:
        st.subheader("글을 확인한 뒤 이미지 방향을 직접 정하세요")
        st.caption(
            "각 이미지의 장면·배경·색감·인물·구도를 따로 적고 한 장씩 생성할 수 있습니다. "
            "생성 후에도 코멘트를 고쳐 다시 만들 수 있습니다."
        )
        st.warning("AI 이미지는 실제 상품 사진이 아닐 수 있습니다. 정확한 색상·로고·디테일은 사용 허가된 공식 상품 이미지를 이용하세요.")

        image_count = st.radio("생성할 이미지 수", [3, 4], horizontal=True, key="image_count")
        uploaded_references = st.file_uploader(
            "원본 상품 이미지 올리기 (선택)",
            type=["png", "jpg", "jpeg", "webp"],
            accept_multiple_files=True,
            key="reference_images",
            help="최대 4장까지 올릴 수 있습니다. 올리지 않으면 상품 정보와 이미지별 코멘트만으로 생성합니다.",
        )
        reference_files = (uploaded_references or [])[:4]
        if uploaded_references and len(uploaded_references) > 4:
            st.info("원본 이미지는 앞의 4장만 사용합니다.")
        if reference_files:
            st.caption("원본의 상품 형태·색상·패턴을 참고해 모든 이미지를 생성합니다. 업로드한 사진의 사용 권한을 확인해주세요.")
            preview_columns = st.columns(min(len(reference_files), 4))
            for preview_index, uploaded in enumerate(reference_files):
                preview_columns[preview_index].image(uploaded, caption=f"원본 {preview_index + 1}", use_container_width=True)
        else:
            st.caption("원본 이미지가 없습니다. 아래의 상품 정보와 코멘트만으로 이미지를 생성합니다.")

        reference_payload = [
            (uploaded.getvalue(), uploaded.type or "image/png")
            for uploaded in reference_files
        ]
        default_comments = [
            "대표 썸네일용. 상품을 돋보이게 하는 밝고 깔끔한 배경, 중앙 중심 구도, 넉넉한 여백.",
            "실생활 사용 장면. 자연스러운 공간과 인물의 동작을 포함하되 광고처럼 과장하지 않기.",
            "상품의 핵심 특징을 이해하기 쉬운 디테일 중심 장면. 가까운 구도와 자연광 사용.",
            "추천 대상이 상품을 활용하는 분위기 장면. 앞의 이미지들과 다른 배경과 카메라 각도.",
        ]

        for index in range(1, image_count + 1):
            with st.container(border=True):
                st.markdown(f"#### 이미지 {index}")
                comment = st.text_area(
                    f"이미지 {index} 생성 코멘트",
                    value=default_comments[index - 1],
                    height=105,
                    key=f"image_comment_{index}",
                    placeholder="예: 아이보리 배경, 옷을 펼쳐 놓은 플랫레이, 따뜻한 오전 자연광, 텍스트 없음",
                )
                final_prompt = build_image_prompt(
                    st.session_state["product"],
                    st.session_state["image_style"],
                    comment,
                    index,
                    bool(reference_payload),
                )
                with st.expander("AI에 전달될 요청 내용 미리보기"):
                    st.code(final_prompt, language=None)

                if st.button(
                    f"이미지 {index} 생성" if index not in st.session_state.get("generated_images", {}) else f"이미지 {index} 다시 생성",
                    type="primary",
                    use_container_width=True,
                    key=f"generate_image_{index}",
                    disabled=not comment.strip(),
                ):
                    try:
                        with st.spinner(f"이미지 {index}을 만들고 있습니다..."):
                            client = OpenAI(api_key=api_key)
                            image_bytes, revised_prompt, original_prompt = generate_image(
                                client,
                                st.session_state["product"],
                                st.session_state["image_style"],
                                comment,
                                index,
                                reference_payload,
                            )
                            st.session_state.setdefault("generated_images", {})[index] = {
                                "bytes": image_bytes,
                                "comment": comment,
                                "original_prompt": original_prompt,
                                "revised_prompt": revised_prompt,
                            }
                    except Exception as exc:
                        st.error(f"이미지 {index} 생성 중 문제가 발생했습니다: {exc}")

                generated = st.session_state.get("generated_images", {}).get(index)
                if generated:
                    st.image(generated["bytes"], caption=f"이미지 {index}: {generated['comment']}", use_container_width=True)
                    st.download_button(
                        f"이미지 {index} 저장",
                        generated["bytes"],
                        file_name=f"blog_image_{index}.png",
                        mime="image/png",
                        use_container_width=True,
                        key=f"download_image_{index}",
                    )
    with comic_tab:
        st.subheader("갈멜의 재미있는 상품 고민 4컷")
        st.caption("스토리 초안을 만든 뒤 장면과 대사를 직접 고치고, 확인이 끝났을 때 만화 이미지를 생성하세요.")
        st.info("갈멜은 웃음과 공감으로 관심을 이끌지만, 허위 할인·불안 조장·가짜 후기는 사용하지 않습니다.")
        comic_c1, comic_c2 = st.columns(2)
        comic_tone = comic_c1.selectbox("스토리 분위기", ["일상 공감형", "위트 있는 구매 고민형", "생활 정보형"], key="galmel_tone")
        comic_style = comic_c2.selectbox("만화 화풍", list(COMIC_STYLES), key="galmel_style")
        comic_direction = st.text_area("갈멜에게 원하는 이야기 방향 (선택)", placeholder="예: 출근할 때 옷 고르기 어려운 갈멜이 편안한 코디를 찾는 이야기", height=90, key="galmel_direction")
        if st.button("갈멜 스토리 초안 만들기", type="primary", use_container_width=True):
            try:
                with st.spinner("갈멜의 4컷 이야기를 구상하고 있습니다..."):
                    client = OpenAI(api_key=api_key)
                    st.session_state["galmel_story"] = generate_galmel_story(client, st.session_state["product"], st.session_state["article"], comic_tone, comic_direction)
                    st.session_state["galmel_edit_version"] = st.session_state.get("galmel_edit_version", 0) + 1
                    st.session_state.pop("galmel_image", None)
                st.success("스토리 초안이 준비되었습니다. 아래 내용을 자유롭게 고쳐주세요.")
            except Exception as exc:
                st.error(f"스토리 생성 중 문제가 발생했습니다: {exc}")

        story = st.session_state.get("galmel_story")
        if story:
            version = st.session_state.get("galmel_edit_version", 0)
            with st.form(f"galmel_editor_{version}"):
                edited_title = st.text_input("만화 제목", value=story.get("title", ""))
                edited_theme = st.text_input("이야기 주제", value=story.get("theme", ""))
                edited_panels = []
                for index, panel in enumerate(story.get("panels", []), 1):
                    st.markdown(f"#### {index}컷")
                    scene = st.text_area("장면", value=panel.get("scene", ""), key=f"galmel_scene_{version}_{index}")
                    dialogue = st.text_input("갈멜의 대사", value=panel.get("dialogue", ""), key=f"galmel_dialogue_{version}_{index}")
                    narration = st.text_input("하단 설명", value=panel.get("narration", ""), key=f"galmel_narration_{version}_{index}")
                    edited_panels.append({"caption": f"{index}컷", "scene": scene, "dialogue": dialogue, "narration": narration})
                edited_closing = st.text_input("마무리 문구", value=story.get("closing", ""))
                save_story = st.form_submit_button("수정한 스토리 저장", use_container_width=True)
            if save_story:
                st.session_state["galmel_story"] = {"title": edited_title, "theme": edited_theme, "panels": edited_panels, "closing": edited_closing}
                st.session_state.pop("galmel_image", None)
                story = st.session_state["galmel_story"]
                st.success("수정한 스토리를 저장했습니다.")

            with st.expander("현재 4컷 스토리 한눈에 보기", expanded=True):
                st.markdown(galmel_story_text(story))
            st.download_button("4컷 스토리 저장", galmel_story_text(story), file_name="galmel_4cut_story.md", mime="text/markdown", use_container_width=True)
            st.warning("AI가 이미지 속 한국어를 틀리게 그릴 수 있습니다. 생성 후 대사와 상품 표현을 꼭 확인해주세요.")
            if st.button("확인한 내용으로 4컷 만화 생성", type="primary", use_container_width=True):
                try:
                    with st.spinner("갈멜 4컷 만화를 그리고 있습니다..."):
                        client = OpenAI(api_key=api_key)
                        comic_bytes, comic_prompt = generate_galmel_comic(client, story, comic_style)
                        st.session_state["galmel_image"] = {"bytes": comic_bytes, "prompt": comic_prompt}
                except Exception as exc:
                    st.error(f"4컷 만화 생성 중 문제가 발생했습니다: {exc}")
            comic = st.session_state.get("galmel_image")
            if comic:
                st.image(comic["bytes"], caption=story.get("title", "갈멜 4컷"), use_container_width=True)
                st.download_button("갈멜 4컷 이미지 저장", comic["bytes"], file_name="galmel_4cut.png", mime="image/png", use_container_width=True)
    with check_tab:
        checks = [
            "글 첫 부분에 경제적 이해관계가 명확히 표시되어 있나요?",
            "현재 가격과 옵션을 상품 페이지에서 다시 확인했나요?",
            "직접 쓰지 않은 상품을 사용한 것처럼 표현하지 않았나요?",
            "효능·최저가·1위 같은 표현에 객관적 근거가 있나요?",
            "제휴 링크가 정상적으로 열리는지 확인했나요?",
            "생성 이미지가 실제 상품 사진으로 오인될 가능성은 없나요?",
        ]
        for item in checks:
            st.checkbox(item)
        st.warning("이 도구는 초안 작성용입니다. 최종 게시 책임은 작성자에게 있으며, 브랜드커넥트의 최신 안내 문구를 우선 적용하세요.")

with st.expander("개인정보와 사용 안내"):
    st.write("입력한 내용은 기본적으로 앱의 현재 세션에서만 사용됩니다. 주문정보·고객정보·로그인정보는 입력하지 마세요.")
    st.write("가격을 자동 수집하거나 네이버 블로그에 자동 게시하지 않습니다. 가격과 링크는 게시 직전에 직접 확인하세요.")

