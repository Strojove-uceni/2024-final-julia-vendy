# app.py
import uuid
import streamlit as st
from helper import AccidentDetectionHelper
from settings import AccidentDetectionSettings
from ultralytics import YOLO
import os
from pathlib import Path

def main():
    settings = AccidentDetectionSettings()
    helper = AccidentDetectionHelper(settings)

    if 'videos' not in st.session_state:
        st.session_state.videos = []

    # Load YOLO model
    if not settings.model_path.exists():
        st.error(f"YOLO model not found at {settings.model_path}. Please ensure the model exists.")
        return

    model = YOLO(str(settings.model_path))

    # Streamlit UI
    st.title("🚗 Accident Detection System")

    st.markdown("""
    Upload up to 6 videos. The system will process each video, detect accidents, and highlight them with bounding boxes. 
    
    Videos with detected accidents will have a:
    - **red border** for "Severe Accident" 
    - **orange border** for "Minor Accident". 
    
    Based on the detected accidents, the system enables you to dispatch the appropriate response team, such as **police**, **medical personnel**, **fire services**, or all units, **depending on the severity** of the incident.
    """)

    uploaded_files = st.file_uploader(
        "Choose up to 6 video files", 
        type=["mp4", "avi", "mov", "mkv"], 
        accept_multiple_files=True
    )

    if uploaded_files:
        if len(uploaded_files) > settings.max_videos:
            st.warning(f"You can upload up to {settings.max_videos} videos at a time.")
            uploaded_files = uploaded_files[:settings.max_videos]

        for idx, uploaded_file in enumerate(uploaded_files):
            # Check if the video is already in session_state
            existing_video = next((video for video in st.session_state.videos if video['name'] == uploaded_file.name), None)
            if not existing_video:
                # Assign a unique ID and save the video
                video_id = str(uuid.uuid4())
                video_filename = f"uploaded_video_{video_id}.{uploaded_file.name.split('.')[-1]}"
                video_path = settings.snapshots_dir.parent / 'uploads' / video_filename
                settings.snapshots_dir.parent.mkdir(parents=True, exist_ok=True)

                with open(video_path, 'wb') as f:
                    f.write(uploaded_file.read())

                # Add video info to session_state
                video_info = {
                    'id': video_id,
                    'name': uploaded_file.name,
                    'path': str(video_path),
                    'accident_detected': False,
                    'severe_accident_detected': False,
                    'processed': False,
                    'dispatch_shown': False,
                    'selected_services': [],
                    'show_success': False
                }
                st.session_state.videos.append(video_info)
                existing_video = video_info

            # Display video information
            st.write(f"### Video {idx+1}: {existing_video['name']}")
            placeholder = st.empty()

            # Process the video if not done yet
            if not existing_video['processed']:
                with st.spinner(f"Processing Video {idx+1}/{len(uploaded_files)}..."):
                    accident_detected, severe_accident_detected = helper.process_video(
                        existing_video['path'], 
                        placeholder, 
                        model
                    )
                    existing_video['accident_detected'] = accident_detected
                    existing_video['severe_accident_detected'] = severe_accident_detected
                    existing_video['processed'] = True

            # Display detection status
            if existing_video['severe_accident_detected']:
                st.markdown("""<div style='color:red;'>🚨 Severe Accident Detected!!! 
                            
                                                        Recommended Response: Notify Police, Paramedics and Fire Services.""", unsafe_allow_html=True)
            elif existing_video['accident_detected']:
                st.markdown("""<div style='color:orange;'>🚨 Minor Accident Detected!
                            
                                                          Recommended Response: Notify Police.""", unsafe_allow_html=True)
            else:
                st.markdown("<div style='color:green;'>✅ **No Accident Detected.**</div>", unsafe_allow_html=True)

            # If accident detected, show dispatch options
            if existing_video['accident_detected']:
                if not existing_video['dispatch_shown']:
                    dispatch_button_label = f"📞 Dispatch Assistance for {existing_video['name']}"
                    if st.button(dispatch_button_label, key=f"dispatch_btn_{existing_video['id']}"):
                        existing_video['dispatch_shown'] = True

                if existing_video['dispatch_shown']:
                    st.subheader("Select Response Teams:")
                    police = st.checkbox("🚓 Police", key=f"police_{existing_video['id']}")
                    medical = st.checkbox("🚑 Paramedics", key=f"medical_{existing_video['id']}")
                    fire = st.checkbox("🔥 Fire Services", key=f"fire_{existing_video['id']}")

                    submit_label = f"🚀 Submit Dispatch for {existing_video['name']}"
                    if st.button(submit_label, key=f"submit_btn_{existing_video['id']}"):
                        selected_services = []
                        if police:
                            selected_services.append("Police")
                        if medical:
                            selected_services.append("Paramedics")
                        if fire:
                            selected_services.append("Fire Services")

                        if selected_services:
                            services_str = ", ".join(selected_services)
                            existing_video['selected_services'] = selected_services
                            existing_video['dispatch_shown'] = False
                            existing_video['show_success'] = True
                        else:
                            st.warning("Please select at least one service to dispatch.")

                # Show success message if dispatch was submitted
                if existing_video.get('show_success'):
                    services_str = ", ".join(existing_video['selected_services'])
                    st.success(f"You chose: {services_str}. We are working on dispatching the selected services.")
                    # Optionally, reset the success flag after showing the message
                    existing_video['show_success'] = False

            st.markdown("---")

if __name__ == "__main__":
    main()

