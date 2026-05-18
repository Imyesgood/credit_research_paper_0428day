"""
로딩 스플래시 스크린 — CSS 타이머 전용 (JS 없음)
app.py에서 st.set_page_config 직후 show_loader() 한 번 호출
"""
import streamlit as st

_LOADER_HTML = """
<style>
#_cr_splash {
    position: fixed;
    inset: 0;
    z-index: 2147483647;
    background: #2D3F38;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    font-family: 'Apple SD Gothic Neo', 'Noto Sans KR', 'Malgun Gothic', sans-serif;
    animation: _cr_out 0.5s ease 2.0s forwards;
    pointer-events: none;
}
@keyframes _cr_out {
    from { opacity: 1; }
    to   { opacity: 0; visibility: hidden; }
}
._cr_eyebrow {
    font-size: 10px;
    font-weight: 400;
    letter-spacing: 4px;
    color: rgba(141, 193, 117, 0.6);
    text-transform: uppercase;
    margin-bottom: 16px;
}
._cr_title {
    font-size: 28px;
    font-weight: 700;
    color: #DDE8C0;
    letter-spacing: -0.6px;
    margin-bottom: 48px;
}
._cr_bar_wrap {
    width: 140px;
    height: 1.5px;
    background: rgba(221, 232, 192, 0.12);
    border-radius: 2px;
    overflow: hidden;
    margin-bottom: 48px;
    position: relative;
}
._cr_bar {
    position: absolute;
    top: 0; left: 0;
    height: 100%;
    background: #8DC175;
    border-radius: 2px;
    animation: _cr_bar_fill 2.0s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}
@keyframes _cr_bar_fill {
    0%   { width: 0%;   }
    50%  { width: 55%;  }
    80%  { width: 82%;  }
    100% { width: 100%; }
}
._cr_caption {
    font-size: 10px;
    color: rgba(221, 232, 192, 0.22);
    letter-spacing: 2px;
}
</style>

<div id="_cr_splash">
    <div class="_cr_eyebrow">채권 크레딧 분석</div>
    <div class="_cr_title">Credit Research</div>
    <div class="_cr_bar_wrap">
        <div class="_cr_bar"></div>
    </div>
    <div class="_cr_caption">loading</div>
</div>
"""


def show_loader() -> None:
    """
    스플래시 로딩 스크린 삽입.
    st.set_page_config() 직후, 다른 st.* 호출 전에 실행.
    CSS 타이머(2s 표시 + 0.5s 페이드)로만 동작 — JS 없음.
    """
    st.markdown(_LOADER_HTML, unsafe_allow_html=True)