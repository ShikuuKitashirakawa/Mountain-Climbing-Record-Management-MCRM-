# AI Coding Agent Instructions for Streamlit + Folium Learning Project

## Project Overview
This is an educational Streamlit application demonstrating interactive map functionality using Folium. The app allows users to click on a map to set coordinates and visualize a radius circle around the selected point.

## Architecture
- **Main App**: `20260102_App.py` - Core application with map interaction
- **Multi-page Structure**: Uses Streamlit's page system with `pages/` directory
- **Map Integration**: Folium maps rendered via `streamlit_folium` component

## Key Patterns

### Session State Management
Use `st.session_state` to persist clicked coordinates across app reruns. Initialize with default Tokyo coordinates (35.6895, 139.6917).

Example from `20260102_App.py`:
```python
if 'clicked_lat' not in st.session_state:
    st.session_state.clicked_lat = 35.6895
if 'clicked_lon' not in st.session_state:
    st.session_state.clicked_lon = 139.6917
```

### Map Click Handling
Capture map clicks using `st_folium()` with `returned_objects` containing `last_clicked` data. Update session state and trigger `st.rerun()` on coordinate changes.

Example pattern:
```python
map_data = st_folium(m, width=800, height=500)
if map_data and map_data["last_clicked"]:
    new_lat = map_data["last_clicked"]["lat"]
    new_lon = map_data["last_clicked"]["lng"]
    if new_lat != st.session_state.clicked_lat or new_lon != st.session_state.clicked_lon:
        st.session_state.clicked_lat = new_lat
        st.session_state.clicked_lon = new_lon
        st.rerun()
```

### Sidebar Configuration
Place coordinate and radius inputs in `st.sidebar` with number inputs formatted to 6 decimal places.

### Multi-page Navigation
Use `st.page_link()` for navigation between pages, referencing file paths directly.

## Dependencies
Core packages in `requirements.txt`:
- `streamlit`
- `folium`
- `streamlit-folium`

## Running the Application
Execute with: `streamlit run 20260102_App.py`

## Code Style Notes
- UI text and comments in Japanese, code logic in English
- Use descriptive variable names (e.g., `clicked_lat`, `clicked_lon`)
- Include disclaimer sections in sidebars for educational apps

## File Structure
- `20260102_App.py`: Main interactive map page
- `pages/page1.py`: Additional page (currently minimal)
- `requirements.txt`: Python dependencies
- `README.md`: Disclaimer only</content>
<parameter name="filePath">c:\Users\kunis\OneDrive\ドキュメント\VS_Code\2025_StreamlitBasicLearning\2025_StreamlitAndFoliumLearn\.github\copilot-instructions.md