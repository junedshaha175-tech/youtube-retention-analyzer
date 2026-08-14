import streamlit as st
import pandas as pd
st.title("YOUTUBE RETENTION TOOL")


# ========== MATRIX THEME ==========
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
    
    .stApp {
        background: #050505;
        color: #00ff41;
        font-family: 'JetBrains Mono', monospace;
    }
    
    h1 { 
        color: #00ff41 !important; 
        text-align: center;
        text-shadow: 0 0 10px #00ff41;
        font-family: 'JetBrains Mono', monospace !important;
    }
    
    h2, h3 { 
        color: #00cc33 !important; 
        font-family: 'JetBrains Mono', monospace !important;
    }
    
    div[data-testid="stFileUploader"] {
        background: #0a0a0a !important;
        border: 1px solid #00ff41 !important;
        border-radius: 4px !important;
    }
    
    .stDataFrame {
        background: #0a0a0a !important;
    }
    
    div[data-testid="stMetric"] {
        background: #0a0a0a;
        border: 1px solid #00ff41;
        border-radius: 4px;
    }
    div[data-testid="stMetric"] label {
        color: #00cc33 !important;
    }
    div[data-testid="stMetric"] div {
        color: #00ff41 !important;
    }
    
    button {
        background: #0a0a0a !important;
        color: #00ff41 !important;
        border: 1px solid #00ff41 !important;
    }
    
    hr {
        border-color: #003300 !important;
    }
    
    .stCaption {
        color: #00aa33 !important;
    }
</style>
""", unsafe_allow_html=True)
# Welcome Card
st.markdown("""
<div style="background: linear-gradient(90deg, rgba(0,255,65,0.1), rgba(0,255,65,0.02)); 
     border: 1px solid #00ff41; 
     border-radius: 8px; 
     padding: 12px 20px; 
     margin: 20px 0 30px 0;
     text-align: center;">
    <span style="color: #00ff41; font-size: 1.2rem; font-weight: 600;">
        👋 Hello Creator! Upload your retention CSV to get started.
    </span>
</div>
""", unsafe_allow_html=True)


with st.expander("📖 How to Use This Tool", expanded=False):
    st.markdown("""
    <div style="color: #00ff41; line-height: 1.8;">
    
    <b>Step 1:</b> YouTube Studio → Select Video → <b>Analytics</b><br>
    <b>Step 2:</b> Left menu mein <b>Audience Retention</b> click karo<br>
    <b>Step 3:</b> Uppr <b>Export</b> ya <b>Download</b> button se <b>CSV</b> save karo<br>
    <b>Step 4:</b> Woh CSV file yahan 👇 upload karo<br><br>
    
    <b>Milega kya?</b><br>
    📈 Retention Graph<br>
    🔴 Drop points (kahan viewers chhode)<br>
    ✅ Spike points (kya accha chala)<br>
    💡 Improvement suggestions<br>
    
    </div>
    """, unsafe_allow_html=True)
   
    # Tutorial Video Embed
    st.markdown("""
    <div style="margin-top: 15px; border: 1px solid #00ff41; border-radius: 8px; overflow: hidden;">
        <iframe width="100%" height="220" 
        src="https://www.youtube.com/embed/U6tJMXdyhIE" 
        title="How to use Retention Analyzer" 
        frameborder="0" 
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
        allowfullscreen>
        </iframe>
    </div>
    <div style="text-align: center; margin-top: 8px; color: #00aa33; font-size: 0.85rem;">
        📺 Watch: Step-by-step tutorial video
    </div>
    """, unsafe_allow_html=True)



uploaded_file=st.file_uploader("Upload your YouTube retention CSV", type=["csv","zip"])

def time_to_seconds(time_str):
    time_str = str(time_str).strip()
    if ":" in time_str:
        parts = time_str.split(":")
        return int(float(parts[0])) * 60 + int(float(parts[1]))
    else:
        return int(float(time_str))


if uploaded_file is not None:
    if not (uploaded_file.name.endswith(".csv") or uploaded_file.name.endswith(".zip")):
        st.error("❌ Only CSV or ZIP files allowed!")
        st.stop()
    
    df=pd.read_csv(uploaded_file)

    if "Video position (%)" in df.columns:
        df.columns = ["Time", "Retention"]
    

    required_cols = ["Time", "Retention"]
    missing = [col for col in required_cols if col not in df.columns]
    
    if missing:
        st.error(f"❌ Wrong CSV! Missing columns: {missing}")
        st.info("""
        **Sahi CSV kaise nikalein:**
        1. YouTube Studio → Content → Select Video
        2. Analytics → Audience retention
        3. Export → CSV
        """)
        st.stop()

    st.write("data loaded successfully!")
    st.dataframe(df)
    st.subheader("📈 Retention curve")
    st.line_chart(df["Retention"])

    st.divider()
    st.subheader("🔍 Retention Analysis")
    df["drop"]=df["Retention"].shift(1)-df["Retention"]

    avg_drop = df["drop"].mean()
    std_drop = df["drop"].std()

    major_threshold = avg_drop + (2 * std_drop)
    minor_threshold = avg_drop + (1 * std_drop)
    spike_threshold = avg_drop - (1.5 * std_drop)

    total_duration = time_to_seconds(df["Time"].max())


    st.caption(f"Major threshold: {major_threshold:.1f}% | Drop threshold: {minor_threshold:.1f}% | Spike threshold: {spike_threshold:.1f}%")


    major_drop_count=0
    drop_count=0
    spike_count=0

    intro_suggested = False
    mid_suggested = False
    end_suggested = False
    spike_intro_suggested = False
    spike_late_suggested = False

    for _,row in df.iterrows():
        time = row["Time"]
        time_sec =time_to_seconds(row["Time"])
        time_pct = (time_sec / total_duration) * 100 if total_duration > 0 else 0


        if row["drop"] > major_threshold:
            major_drop_count+=1
            st.markdown(f"🔴 MAJOR DROP at {time} — lost {int(row['drop'])}% viewers")
            if time_pct < 10 and not intro_suggested:
                st.markdown("   💡 Suggestion: Intro is too weak — start with a strong hook in the first 10%")
                intro_suggested = True
            elif time_pct < 50 and not mid_suggested:
                st.markdown("   💡 Suggestion: Content is slowing down — add B-roll, jump cuts, or a twist here")
                mid_suggested = True
            elif not end_suggested:
                st.markdown("   💡 Suggestion: End retention is falling — shorten or add a cliffhanger/CTA earlier")
                end_suggested = True
           


        elif row["drop"] >minor_threshold:
            drop_count+=1
            st.markdown(f"⚠️ Drop at {time} — lost {int(row['drop'])}% viewers")
            if time_pct < 10 and not intro_suggested:
                st.markdown("   💡 Suggestion: Intro needs tightening — remove filler words and get to the point faster")
                intro_suggested = True
            elif time_pct < 50 and not mid_suggested:
                st.markdown("   💡 Suggestion: This section is dragging — trim dead air or add visual changes")
                mid_suggested = True
            elif not end_suggested:
                st.markdown("   💡 Suggestion: Viewer interest fading — add a mini-hook or question to re-engage")
                end_suggested = True
            

        elif row["drop"] < spike_threshold:
            spike_count+=1
            st.markdown(f"✅ Spike at {time} — gained {abs(int(row['drop']))}% viewers")
             if time_pct < 15 and not spike_intro_suggested:
                st.markdown("   💡 Suggestion: This hook works — reuse this exact pattern in your next intro")
                spike_intro_suggested = True
             elif not spike_late_suggested:
                 st.markdown("   💡 Suggestion: Strong moment — highlight this in thumbnail/title or make a Shorts clip")
                 spike_late_suggested = True
           


    st.divider()
    st.subheader("📈 Summary")

    col1,col2,col3=st.columns(3)
    col1.metric("🔴 Major Drops", major_drop_count)
    col2.metric("⚠️ Drops", drop_count)
    col3.metric("✅ Spikes", spike_count)


    issues = major_drop_count + drop_count
    if issues == 0:
        st.success("STATUS: PERFECT")
    elif issues <= 3:
        st.warning("STATUS: OPTIMIZABLE")
    else:
        st.error("STATUS: CRITICAL")


    st.markdown("""
    <div style="text-align:center; color:#00ff41; margin-top:30px; padding:15px; 
         border-top:1px solid #003300; font-size:0.9rem;">
        🚀 Built by <b>@4BVORTEX</b> | 
        <a href="https://www.youtube.com/@4BVORTEX" target="_blank" style="color:#feca57;">
        📺 Subscribe
        </a>
    </div>
    """, unsafe_allow_html=True)

else:
    
    pass     




           


