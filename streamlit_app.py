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


def generate_image(client, product, style):
    prompt = f"""
Create a polished Korean commerce blog hero image for a product review.
Product: {product['brand']} {product['name']}.
Key visual facts: {product['features']}.
Style: {style}. Clean editorial product photography, natural lighting,
generous negative space, no logos not supplied, no price, no badges, no text,
no unverifiable claims, landscape composition suitable for a blog cover.
"""
    response = client.responses.create(
        model=secret("IMAGE_ORCHESTRATOR_MODEL", "gpt-5.6-luna"),
        input=prompt,
        tools=[
            {
                "type": "image_generation",
                "model": secret("IMAGE_MODEL", "gpt-image-2.5-flare"),
                "size": "1536x1024",
            }
        ],
    )
    for item in response.output:
        if getattr(item, "type", "") == "image_generation_call":
            return base64.b64decode(item.result), getattr(item, "revised_prompt", prompt)
    raise RuntimeError("이미지 결과를 받지 못했습니다.")


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
        try:
            with st.spinner("자료를 정리해 블로그 초안을 작성하고 있습니다..."):
                st.session_state["article"] = generate_article(client, product, competitors, settings)
            st.success("초안이 완성되었습니다. 사실관계와 가격을 꼭 확인해주세요.")
        except Exception as exc:
            st.error(f"글 생성 중 문제가 발생했습니다: {exc}")

if st.session_state.get("article"):
    st.divider()
    article_tab, image_tab, check_tab = st.tabs(["블로그 초안", "대표 이미지", "발행 전 점검"])
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
        st.caption("상품의 실제 외형과 다를 수 있으므로 생성 이미지는 대표 이미지·분위기 컷으로만 사용하세요.")
        if st.button("대표 이미지 생성", type="primary", use_container_width=True):
            try:
                with st.spinner("대표 이미지를 만들고 있습니다..."):
                    client = OpenAI(api_key=api_key)
                    image_bytes, revised_prompt = generate_image(
                        client,
                        st.session_state["product"],
                        st.session_state["image_style"],
                    )
                    st.session_state["image_bytes"] = image_bytes
                    st.session_state["image_prompt"] = revised_prompt
            except Exception as exc:
                st.error(f"이미지 생성 중 문제가 발생했습니다: {exc}")
        if st.session_state.get("image_bytes"):
            st.image(st.session_state["image_bytes"], use_container_width=True)
            st.download_button(
                "이미지 저장",
                st.session_state["image_bytes"],
                file_name="blog_hero.png",
                mime="image/png",
                use_container_width=True,
            )
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


