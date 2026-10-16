import random

import streamlit as st
import pandas as pd

from thumbnail import (
    LAYOUTS, MAX_TITLE_CHARS, STYLES, font_ok, load_image as load_thumb_image,
    make_thumbnail, to_jpeg_bytes, to_png_bytes,
)

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



# ========== AUTO THUMBNAIL MAKER ==========
with st.expander("🎨 Auto Thumbnail Maker (NEW)", expanded=False):
    st.caption("Title likho, styles chuno — 1280x720 thumbnails ready. Free, no signup.")

    thumb_title = st.text_input(
        "Thumbnail title", max_chars=MAX_TITLE_CHARS, key="thumb_title",
        placeholder="I survived 100 days in Minecraft",
    )
    tcol1, tcol2 = st.columns(2)
    thumb_highlight = tcol1.text_input(
        "Highlight word(s) — optional", key="thumb_highlight",
        help="Leave empty and the tool auto-highlights a number or the last word.",
    )
    thumb_badge = tcol2.text_input("Corner badge — optional", max_chars=14, key="thumb_badge",
                                   placeholder="EP 12")

    LAYOUT_HELP = {
        "Big headline": "Bada title ek side, character doosri side.",
        "Small label": "Pro gaming look: chhota label (1-3 words) top me, character bada. Best for face + game.",
        "Versus": "Do characters aamne-saamne (NOOB vs PRO, Me vs Friend). Title me 'vs' likho.",
    }
    thumb_layout = st.radio("Layout", list(LAYOUTS), index=1, horizontal=True, key="thumb_layout")
    st.caption(LAYOUT_HELP[thumb_layout])
    is_versus = thumb_layout == "Versus"

    bcol1, bcol2 = st.columns(2)
    thumb_bg_file = bcol1.file_uploader("Background image — optional (game screenshot)",
                                        type=["png", "jpg", "jpeg", "webp"], key="thumb_bg")
    thumb_fg_file = bcol2.file_uploader(
        "Character 1 (left)" if is_versus else "Face / character — optional (transparent PNG looks best)",
        type=["png", "jpg", "jpeg", "webp"], key="thumb_fg")
    thumb_fg2_file = None
    if is_versus:
        thumb_fg2_file = st.file_uploader("Character 2 (right) — transparent PNG",
                                          type=["png", "jpg", "jpeg", "webp"], key="thumb_fg2")
        if not (thumb_fg_file and thumb_fg2_file):
            st.info("Versus layout ke liye dono characters upload karo — warna normal layout banega.")

    st.caption("💡 Best result: background = game screenshot, "
               "character = transparent PNG (remove.bg ya Canva 'Background Remover').")

    scol1, scol2 = st.columns(2)
    thumb_side = "Right"
    if not is_versus:
        thumb_side = scol1.radio("Character position", ["Right", "Left"], horizontal=True,
                                 key="thumb_side")
    thumb_blur = scol2.checkbox("Blur background (pro look)", value=True, key="thumb_blur")

    thumb_styles = st.multiselect("Styles", list(STYLES.keys()), default=list(STYLES.keys()),
                                  key="thumb_styles")
    thumb_border = st.checkbox("Colored border", value=False, key="thumb_border")

    max_words = {"Big headline": 6, "Small label": 4, "Versus": 4}[thumb_layout]
    if len(thumb_title.split()) > max_words:
        st.info(f"Title thoda lamba hai — is layout me {max_words} words tak sabse achha dikhta hai.")

    if thumb_title.strip() and not font_ok(thumb_title):
        st.warning("Hindi font not found on this system — Hindi letters may show as boxes. "
                   "English titles work fine.")

    if st.button("✨ Generate thumbnails", key="thumb_generate"):
        if not thumb_title.strip():
            st.error("❌ Pehle title likho.")
        elif not thumb_styles:
            st.error("❌ Kam se kam ek style chuno.")
        else:
            try:
                bg_img = load_thumb_image(thumb_bg_file) if thumb_bg_file else None
                fg_img = load_thumb_image(thumb_fg_file) if thumb_fg_file else None
                fg_img2 = load_thumb_image(thumb_fg2_file) if thumb_fg2_file else None
                seed = random.randint(0, 10_000)
                results = {}
                with st.spinner("Making thumbnails..."):
                    for style_name in thumb_styles:
                        img = make_thumbnail(
                            thumb_title, style_name, highlight=thumb_highlight,
                            badge=thumb_badge, bg_image=bg_img, fg_image=fg_img,
                            seed=seed, border=thumb_border,
                            side=thumb_side.lower(), blur_bg=thumb_blur,
                            layout=thumb_layout, fg_image2=fg_img2,
                        )
                        results[style_name] = (to_png_bytes(img), to_jpeg_bytes(img))
                st.session_state["thumb_results"] = results
            except Exception:
                st.error("❌ Could not read one of the images. Try a different PNG/JPG file.")

    thumb_results = st.session_state.get("thumb_results")
    if thumb_results:
        rcols = st.columns(2)
        for i, (style_name, (png_bytes, jpg_bytes)) in enumerate(thumb_results.items()):
            with rcols[i % 2]:
                st.image(png_bytes, caption=style_name, width="stretch")
                dcol1, dcol2 = st.columns(2)
                slug = style_name.lower().replace(" ", "_")
                dcol1.download_button("⬇ PNG", png_bytes, file_name=f"thumbnail_{slug}.png",
                                      mime="image/png", key=f"dl_png_{slug}")
                dcol2.download_button("⬇ JPG (<2MB)", jpg_bytes, file_name=f"thumbnail_{slug}.jpg",
                                      mime="image/jpeg", key=f"dl_jpg_{slug}")
        st.caption("Tip: click Generate again for a fresh background pattern.")


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


      
    all_issues = []
    for _,row in df.iterrows():
        time = row["Time"]
        time_sec =time_to_seconds(row["Time"])
        time_pct = (time_sec / total_duration) * 100 if total_duration > 0 else 0

        
        if row["drop"] > major_threshold:
            all_issues.append({
                "type": "major",
                "time": time,
                "pct": time_pct,
                "drop": int(row['drop'])
            })
        elif row["drop"] > minor_threshold:
            all_issues.append({
                "type": "minor",
                "time": time,
                "pct": time_pct,
                "drop": int(row['drop'])
            })
        elif row["drop"] < spike_threshold:
            all_issues.append({
                "type": "spike",
                "time": time,
                "pct": time_pct,
                "drop": abs(int(row['drop']))
            })

    severity_order = {"major": 0, "minor": 1, "spike": 2}
    all_issues.sort(key=lambda x: (severity_order[x["type"]], -x["drop"]))


    major_drop_count=0
    drop_count=0
    spike_count=0

    for i in all_issues:
        if i["type"]=="major":
            major_drop_count+=1
        elif i["type"]=="minor":
            drop_count+=1
        else:
            spike_count+=1


    # FLAGS — ek baar suggestion, baar baar nahi
    intro_suggested = False
    mid_suggested = False
    end_suggested = False
    spike_intro_suggested = False
    spike_late_suggested = False

    top_n = 5
    
    if len(all_issues) == 0:
        st.success("🎉 No issues found! Retention is solid.")
    else:
        st.markdown(f"**{len(all_issues)} issues found — showing top {min(top_n, len(all_issues))} critical:**")
        
        for issue in all_issues[:top_n]:
            time = issue["time"]
            time_pct = issue["pct"]
            
            if issue["type"] == "major":
                st.markdown(f"🔴 MAJOR DROP at {time} — lost {issue['drop']}% viewers")
                if time_pct < 10 and not intro_suggested:
                    st.markdown("   💡 Suggestion: Intro is too weak — start with a strong hook in the first 10%")
                    intro_suggested = True
                elif time_pct < 50 and not mid_suggested:
                    st.markdown("   💡 Suggestion: Content is slowing down — add B-roll, jump cuts, or a twist here")
                    mid_suggested = True
                elif not end_suggested:
                    st.markdown("   💡 Suggestion: End retention is falling — shorten or add a cliffhanger/CTA earlier")
                    end_suggested = True
                    
            elif issue["type"] == "minor":
                st.markdown(f"⚠️ Drop at {time} — lost {issue['drop']}% viewers")
                if time_pct < 10 and not intro_suggested:
                    st.markdown("   💡 Suggestion: Intro needs tightening — remove filler words and get to the point faster")
                    intro_suggested = True
                elif time_pct < 50 and not mid_suggested:
                    st.markdown("   💡 Suggestion: This section is dragging — trim dead air or add visual changes")
                    mid_suggested = True
                elif not end_suggested:
                    st.markdown("   💡 Suggestion: Viewer interest fading — add a mini-hook or question to re-engage")
                    end_suggested = True
                    
            else:
                st.markdown(f"✅ Spike at {time} — gained {issue['drop']}% viewers")
                if time_pct < 15 and not spike_intro_suggested:
                    st.markdown("   💡 Suggestion: This hook works — reuse this exact pattern in your next intro")
                    spike_intro_suggested = True
                elif not spike_late_suggested:
                    st.markdown("   💡 Suggestion: Strong moment — highlight this in thumbnail/title or make a Shorts clip")
                    spike_late_suggested = True

        remaining = len(all_issues) - top_n
        if remaining > 0:
            with st.expander(f"📉 View remaining {remaining} issues", expanded=False):
                for issue in all_issues[top_n:]:
                    if issue["type"] == "major":
                        st.markdown(f"🔴 MAJOR DROP at {issue['time']} — lost {issue['drop']}% viewers")
                    elif issue["type"] == "minor":
                        st.markdown(f"⚠️ Drop at {issue['time']} — lost {issue['drop']}% viewers")
                    else:
                        st.markdown(f"✅ Spike at {issue['time']} — gained {issue['drop']}% viewers")
        
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




           


