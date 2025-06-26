import os
import tempfile
import streamlit as st
from langchain_openai import ChatOpenAI
from openai import OpenAI
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader, PyPDFLoader, Docx2txtLoader

# 初始化ChatOpenAI模型
model = ChatOpenAI(
    base_url='https://api.deepseek.com/',
    model='deepseek-reasoner',
    temperature=0,
    api_key=st.secrets["OPENAI_API_KEY"]  # 修改为使用st.secrets
)

def get_answer(question: str, strict_file_mode: bool = False):
    try:
        client = OpenAI(
            base_url='https://api.deepseek.com',
            api_key=st.secrets["OPENAI_API_KEY"]  # 修改为使用st.secrets
        )

        messages = []
        for role, content in st.session_state['messages'][:-1]:
            messages.append({
                'role': 'assistant' if role == 'ai' else 'user',
                'content': content
            })

        messages.append({'role': 'user', 'content': question})

        if strict_file_mode and st.session_state['file_content']:
            messages[-1][
                'content'] = f"请严格根据以下文件内容回答问题，如果文件内容中没有相关信息，请回答'根据文件内容无法回答该问题':\n\n文件内容:\n{st.session_state['file_content']}\n\n问题:{question}"

        response = client.chat.completions.create(
            model='deepseek-reasoner',
            messages=messages,
            temperature=0,
            max_tokens=1024
        )

        return response.choices[0].message.content
    except Exception as err:
        print(err)
        return '暂时无法提供回复，请检查你的配置是否正确'


def load_file(uploaded_file):
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
        for doc in docs:
            content += doc.page_content + "\n\n"

        return content
    except Exception as e:
        return f"文件加载失败: {str(e)}"
    finally:
        if tmp_file_path and os.path.exists(tmp_file_path):
            try:
                os.unlink(tmp_file_path)
            except:
                pass


# 初始化会话状态
if 'messages' not in st.session_state:
    st.session_state['messages'] = [('🐯', '(ฅฅ´ω`ฅฅ)你好，我是你的AI助手晓生，为你解决所有问题')]
if 'file_content' not in st.session_state:
    st.session_state['file_content'] = ""
if 'strict_file_mode' not in st.session_state:
    st.session_state['strict_file_mode'] = False

# 页面标题
st.write('##   🐯江湖百晓生 ')

# 侧边栏设置
with st.sidebar:
    st.title('文件上传')

    # 文件上传区域
    uploaded_file = st.file_uploader(
        "📤上传文件 (txt/pdf/docx)",
        type=['txt', 'pdf', 'docx'],
        help="上传文件后，回答将严格基于文件内容"
    )

    # 严格模式开关
    st.session_state['strict_file_mode'] = st.checkbox(
        "严格文件模式",
        value=st.session_state['strict_file_mode'],
        help="开启后回答将仅基于文件内容"
    )

    if uploaded_file:
        with st.spinner('正在解析文件内容...'):
            file_content = load_file(uploaded_file)
            if file_content.startswith("文件加载失败"):
                st.error(file_content)
                st.session_state['file_content'] = ""
            else:
                st.session_state['file_content'] = file_content
                st.success("✅文件解析完成！")
                st.text_area("📝 文件内容预览",
                             value=file_content[:1000] + ("..." if len(file_content) > 1000 else ""),
                             height=200)

    st.title('对话管理')

    # 清空所有对话按钮
    if st.button('🔄 清空所有对话'):
        st.session_state['messages'] = [('🐯', '(ฅ´ω`ฅ)对话历史已清空，请问我新的问题吧')]
        st.rerun()

    st.divider()
    st.title('对话记录')

    # 显示可删除的对话历史
    for idx, (role, content) in enumerate(reversed(st.session_state['messages'])):
        if role == 'human':
            truncated_content = content[:20] + ("..." if len(content) > 20 else "")
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"[{truncated_content}](#{idx})", unsafe_allow_html=True)
            with col2:
                if st.button('🗑️', key=f"del_{idx}", type="secondary"):
                    # 删除指定对话
                    del st.session_state['messages'][len(st.session_state['messages']) - 1 - idx]
                    del st.session_state['messages'][len(st.session_state['messages']) - 1 - idx]
                    st.rerun()

# 显示历史对话
for idx, (role, content) in enumerate(st.session_state['messages']):
    message_container = st.container()
    with message_container:
        st.chat_message(role).write(content)
        st.markdown(f'<a name="{len(st.session_state["messages"]) - idx - 1}"></a>', unsafe_allow_html=True)

# 用户输入
user_input = st.chat_input(placeholder='遇事不决，问百晓生')
if user_input:
    st.session_state['messages'].append(('human', user_input))
    st.chat_message('human').write(user_input)

    with st.spinner('晓生思考中，少侠莫急...'):
        answer = get_answer(
            user_input,
            strict_file_mode=st.session_state['strict_file_mode']
        )
        st.chat_message('🐯').write(answer)
        st.session_state['messages'].append(('🐯', answer))
