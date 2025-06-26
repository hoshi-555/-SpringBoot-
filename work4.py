import os
import tempfile
import streamlit as st
from langchain_openai import ChatOpenAI
from openai import OpenAI
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader, PyPDFLoader, Docx2txtLoader


# ======================
# 安全密钥管理模块
# ======================
def get_api_key():
    """安全获取API密钥的优先级逻辑：
    1. 优先从Streamlit Secrets读取（生产环境）
    2. 其次从.env文件读取（开发环境）
    3. 最后尝试直接读取环境变量
    """
    # 检查Streamlit Secrets
    if hasattr(st, 'secrets') and 'OPENAI_API_KEY' in st.secrets:
        return st.secrets["OPENAI_API_KEY"]

    # 检查.env文件
    try:
        load_dotenv()
        if os.getenv("OPENAI_API_KEY"):
            return os.getenv("OPENAI_API_KEY")
    except:
        pass

    # 最终检查环境变量
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        st.error("❌ 未检测到API密钥配置！请通过以下方式之一配置：\n"
                 "1. 在Streamlit Secrets中添加（生产环境）\n"
                 "2. 在项目根目录创建.env文件（开发环境）\n"
                 "3. 直接设置系统环境变量")
        st.stop()
    return api_key


# ======================
# 核心功能模块
# ======================
def initialize_llm():
    """初始化语言模型"""
    return ChatOpenAI(
        base_url='https://api.deepseek.com/',
        model='deepseek-reasoner',
        temperature=0,
        api_key=get_api_key()  # 使用安全获取的密钥
    )


def get_answer(question: str, strict_file_mode: bool = False):
    """获取AI回答的核心逻辑"""
    try:
        client = OpenAI(
            base_url='https://api.deepseek.com',
            api_key=get_api_key()  # 统一使用密钥获取方法
        )

        messages = []
        for role, content in st.session_state['messages'][:-1]:
            messages.append({
                'role': 'assistant' if role == 'ai' else 'user',
                'content': content
            })

        messages.append({'role': 'user', 'content': question})

        if strict_file_mode and st.session_state['file_content']:
            messages[-1]['content'] = (
                "请严格根据以下文件内容回答问题，如果文件内容中没有相关信息，请回答'根据文件内容无法回答该问题':\n\n"
                f"文件内容:\n{st.session_state['file_content']}\n\n"
                f"问题:{question}"
            )

        response = client.chat.completions.create(
            model='deepseek-reasoner',
            messages=messages,
            temperature=0,
            max_tokens=512
        )
        return response.choices[0].message.content

    except Exception as err:
        st.error(f"请求API时出错: {str(err)}")
        return '暂时无法提供回复，请检查配置或稍后再试'


@st.cache_resource(show_spinner=False)
def load_file(uploaded_file):
    """安全加载上传文件并缓存"""
    file_type = uploaded_file.name.split('.')[-1].lower()
    content = ""
    tmp_file_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_type}") as tmp_file:
            file_content = uploaded_file.getvalue()
            tmp_file.write(file_content if isinstance(file_content, bytes) else file_content.encode('utf-8'))
            tmp_file_path = tmp_file.name

        if file_type == 'txt':
            loader = TextLoader(tmp_file_path, encoding='utf-8')
        elif file_type == 'pdf':
            loader = PyPDFLoader(tmp_file_path)
        elif file_type == 'docx':
            loader = Docx2txtLoader(tmp_file_path)
        else:
            return "不支持的文件类型"

        docs = loader.load()
        content = "\n\n".join(doc.page_content for doc in docs)
        return content

    except Exception as e:
        st.error(f"文件加载失败: {str(e)}")
        return ""
    finally:
        if tmp_file_path and os.path.exists(tmp_file_path):
            try:
                os.unlink(tmp_file_path)
            except:
                pass


# ======================
# 界面模块
# ======================
def init_session_state():
    """初始化会话状态"""
    if 'messages' not in st.session_state:
        st.session_state['messages'] = [('🐯', '(ฅ´ω`ฅ)你好，我是你的AI助手晓生，为你解决所有问题')]
    if 'file_content' not in st.session_state:
        st.session_state['file_content'] = ""
    if 'strict_file_mode' not in st.session_state:
        st.session_state['strict_file_mode'] = False


def setup_sidebar():
    """配置侧边栏"""
    with st.sidebar:
        st.title('⚙️ 设置中心')

        # 文件上传区域
        uploaded_file = st.file_uploader(
            "📤 上传知识文件 (txt/pdf/docx)",
            type=['txt', 'pdf', 'docx'],
            help="上传后可在严格模式下基于文件内容问答"
        )

        # 严格模式开关
        st.session_state['strict_file_mode'] = st.toggle(
            " 严格文件模式",
            value=st.session_state['strict_file_mode'],
            help="开启后回答将严格限定在文件内容范围内"
        )

        if uploaded_file:
            with st.spinner('正在解析文件内容...'):
                file_content = load_file(uploaded_file)
                if file_content:
                    st.session_state['file_content'] = file_content
                    st.success("✅ 文件解析完成！")
                    with st.expander("📝 内容预览"):
                        st.text(file_content[:1000] + ("..." if len(file_content) > 1000 else ""))

        # 对话管理
        st.divider()
        if st.button('🔄 清空对话历史', use_container_width=True):
            st.session_state['messages'] = [('ai', '(ฅฅ´ω`ฅฅ)对话历史已清空，请问我新的问题吧')]
            st.rerun()

        st.divider()
        st.caption("💡 提示：上传文件后开启严格模式可获得精准回答")


# ======================
# 主程序
# ======================
def main():
    # 初始化配置
    st.set_page_config(
        page_title="江湖百晓生",
        page_icon="🐯",
        layout="centered"
    )

    init_session_state()
    st.title('🐯 江湖百晓生')
    setup_sidebar()

    # 显示历史对话
    for idx, (role, content) in enumerate(st.session_state['messages']):
        with st.chat_message(role):
            st.write(content)
            if role == 'ai':
                st.markdown(f'<a name="{idx}"></a>', unsafe_allow_html=True)

    # 用户输入处理
    if prompt := st.chat_input("遇事不决，问百晓生"):
        st.session_state['messages'].append(('human', prompt))

        with st.chat_message("human"):
            st.write(prompt)

        with st.chat_message("🐯"):
            with st.spinner(' 晓生思考中,少侠稍等片刻...'):
                response = get_answer(prompt, st.session_state['strict_file_mode'])
                st.write(response)
                st.session_state['messages'].append(('ai', response))


if __name__ == "__main__":
    main()