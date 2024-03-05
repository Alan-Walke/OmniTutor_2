from raw_functions import *
from status_display import *
from openai import OpenAI
import streamlit as st

def app():
    initialize_session_state()

    with st.sidebar:
        api_key = st.text_input('🔑 Your OpenAI API key:', 'sk-...')
        use_35 = st.checkbox('Use GPT-3.5 (GPT-4 is default)')
        st.image("https://siyuan-harry.oss-cn-beijing.aliyuncs.com/oss://siyuan-harry/WechatIMG1729.jpg")
        added_files = st.file_uploader('📁 Upload .md or .pdf files, simultaneous mixed upload both types is supported.', type=['.md','.pdf'], accept_multiple_files=True)
        with st.expander('⚙️ Customize my course'):
            num_lessons = st.slider('How many lessons do you want this course to have?', min_value=2, max_value=15, value=5, step=1)
            custom_options = st.multiselect(
                'Preferred teaching style :grey[(Recommend new users not to select)]',
                ['More examples', 'More excercises', 'Easier to learn'],
                max_selections = 2
            )
            ss.language = 'English'
            Chinese = st.checkbox('Output in Chinese')
        btn_next = st.button('Okay, next learning step! ⏩️')
    
    # unchangable layout
    st.title("OmniTutor 2.0")
    st.subheader("Your personalized :blue[AI Knowledge Engine] 🦉")
    st.markdown("""
        <style>
            .footer {
                position: fixed;
                bottom: 0;
                right: 10px;
                width: auto;
                background-color: transparent;
                text-align: right;
                padding-right: 10px;
                padding-bottom: 10px;
            }
        </style>
        <div class="footer">Made with 🧡 by Siyuan</div>
    """, unsafe_allow_html=True)
    
    user_question = st.chat_input("Enter your questions when learning...")

    #displaying current status
    #if ss.start_learning == 1:
    #    display_current_status(write_description, description)
    display_main_page(ss.main_page_displayed)

    if btn_next:
        ss.main_page_displayed = False
        if api_key !="" and api_key.startswith("sk-") and len(api_key) == 51 and added_files:
            ss.start_learning = 1
            ss.num_lessons = num_lessons
            ss.style_options = add_prompt_course_style(custom_options)
            if ss["OPENAI_API_KEY"] == '':
                ss["OPENAI_API_KEY"] = api_key
                st.success("✅ API Key stored successfully!")
            if Chinese:
                ss.language = "Chinese"
            if use_35:
                ss["openai_model"] = 'gpt-3.5-turbo-1106'
            client = OpenAI(api_key = ss["OPENAI_API_KEY"])

            col1, col2 = st.columns([0.6,0.4])
            with col1:
                if ss.course_outline_list == []:
                    ss.temp_file_paths = initialize_file(added_files)
                    ss.chroma_collection = initialize_vdb(ss.temp_file_paths)
                    ss.course_outline_list = initialize_outline(client, ss.temp_file_paths, num_lessons, ss.language, ss["openai_model"])
                elif ss.course_outline_list != [] and ss.course_content_list == []:
                    regenerate_outline(ss.course_outline_list)
                    ss.lesson_counter = 1
                    new_lesson = visualize_new_content(
                        client, 
                        ss.lesson_counter, 
                        ss.course_outline_list[ss.lesson_counter-1], 
                        ss.chroma_collection, 
                        ss.language, 
                        ss.style_options, 
                        ss["openai_model"]
                    )
                    ss.course_content_list.append(new_lesson)
                else:
                    if ss.lesson_counter < ss.num_lessons:
                        regenerate_outline(ss.course_outline_list)
                        regenerate_content(ss.course_content_list)
                        ss.lesson_counter += 1
                        new_lesson = visualize_new_content(
                            client,
                            ss.lesson_counter,
                            ss.course_outline_list[ss.lesson_counter-1],
                            ss.chroma_collection,
                            ss.language, 
                            ss.style_options, 
                            ss["openai_model"]
                        )
                        ss.course_content_list.append(new_lesson)
                    elif ss.lesson_counter >= ss.num_lessons:
                        display_current_status_col1()
                        #让用户下载课程的文稿markdown
                        course_md = convert_markdown_string(ss.course_outline_list,ss.course_content_list)
                        st.download_button(
                            label="Download Course Script",
                            data=course_md,
                            file_name='OmniTutor_Your_Course.md',
                        )
            with col2:
                display_current_status_col2()
        elif len(ss["OPENAI_API_KEY"]) != 51 and added_files:
            ss.main_page_displayed = False
            display_warning_api_key()
            ss.main_page_displayed = True
        elif not added_files:
            ss.main_page_displayed = False
            display_warning_upload_materials()
            ss.main_page_displayed = True


    if user_question:
        ss.main_page_displayed = False
        if len(ss["OPENAI_API_KEY"]) != 51:
            display_warning_api_key()
            display_current_status()
        elif ss["OPENAI_API_KEY"] != '' and ss.chroma_collection == '':
            display_warning_upload_materials_vdb()
            display_current_status()
        else:
            client = OpenAI(api_key = ss["OPENAI_API_KEY"])
            col1, col2 = st.columns([0.6,0.4])
            with col1:
                display_current_status_col1()
            with col2:
                st.caption(''':blue[AI Assistant]: Ask this TA any questions related to this course and get direct answers. :sunglasses:''')

                with st.chat_message("assistant"):
                    st.markdown("Hello👋, how can I help you today? 😄")

                # Display chat messages from history on app rerun
                for message in ss.messages_ui:
                    with st.chat_message(message["role"]):
                        st.markdown(message["content"])
                
                #更新ui上显示的聊天记录
                ss.messages_ui.append({"role": "user", "content": user_question})
                # Display new user question.
                with st.chat_message("user"):
                    st.markdown(user_question)

                retrieved_chunks_for_user = searchVDB(user_question, ss.chroma_collection)
                prompt = decorate_user_question(user_question, retrieved_chunks_for_user)
                ss.messages.append({"role": "user", "content": prompt})

                # Display assistant response in chat message container
                with st.chat_message("assistant"):
                    full_response = get_visualize_stream_completion_from_messages(
                        client,
                        messages=[
                            {"role": m["role"], "content": m["content"]}
                            for m in st.session_state.messages #用chatbot那边的隐藏消息记录
                        ],
                        model=ss["openai_model"]
                    )
                ss.messages.append({"role": "assistant", "content": full_response})
                ss.messages_ui.append({"role": "assistant", "content": full_response})

if __name__ == "__main__":
    app()

    