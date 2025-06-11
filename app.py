import streamlit as st
import pandas as pd
import json
import math
from streamlit_gsheets import GSheetsConnection

# Generate floating point ranges with specified step size, useful for creating measurement options
def frange(start, stop, step):
    while start < stop:
        yield start
        start += step

# Standardize category names by converting to lowercase and removing whitespace to ensure consistent comparisons
def normalize_category(category_name):
    return category_name.lower().strip() if category_name else category_name

# Calculate recommended internal opening diameter based on user's measurements and sleeve category (low/medium/high)
def get_recommended_opening_diameter(user_diameter, category_name):
    category = normalize_category(category_name)
    
    if category in ["low", "medium"]:
        ranges = [
            {'min': 1, 'max': 1.25, 'recommendation': 0.9},
            {'min': 1.25, 'max': 1.5, 'recommendation': 1.0},
            {'min': 1.5, 'max': 1.825, 'recommendation': 1.125},
            {'min': 1.825, 'max': 2, 'recommendation': 1.25},
            {'min': 2, 'max': 2.15, 'recommendation': 1.375},
            {'min': 2.15, 'max': 100, 'recommendation': 'N/A'},
        ]
    else:
        ranges = [
            {'min': 1, 'max': 1.25, 'recommendation': 'N/A'},
            {'min': 1.25, 'max': 1.4, 'recommendation': 1.0},
            {'min': 1.4, 'max': 1.6, 'recommendation': 1.125},
            {'min': 1.6, 'max': 1.875, 'recommendation': 1.25},
            {'min': 1.875, 'max': 2.25, 'recommendation': 1.375},
            {'min': 2.25, 'max': 100, 'recommendation': 1.5},
        ]
    
    for range_item in ranges:
        if range_item['min'] <= user_diameter < range_item['max']:
            return range_item['recommendation']
    
    return None

# Configure Streamlit page settings including title, icon, and menu items with links to support and documentation
st.set_page_config(
    page_title="Sleeve Selector",
    page_icon="🍆",
    menu_items={
        'About': f"""
        Input your length and diameter to show compatible sleeves. A compatible sleeve
        has a total diameter larger than you, a max interior length as long as you, and an opening
        small enough or large enough to give you a proper, snug fit.
                
        We will also show the total girth of the sleeve when worn with the recommended diameter.
        No more guesswork when comparing models!
        """
    }
)

# Title 
st.title('Sleeve Selector :eggplant:')
st.info(''' 
        Find the perfect sleeve and fit according to Blissfull Creation's [How to Order](https://blissfullcreations.com/pages/how-to-order) guide. 
          
        Select your penis dimensions below to find compatible sized sleeves, while also being provided
        a Recommended Internal Dimensions for ordering.
    ''')

# Pre-compute and cache measurement options to avoid recalculating on every page load
@st.cache_data
def get_select_options():
    diameter_options = [round(x, 3) for x in list(frange(1, 3.125, 0.125))]
    length_options = [round(x, 2) for x in list(frange(2, 9.25, 0.25))]
    return diameter_options, length_options

# Fetch product data from Google Sheets with 10-minute cache, falling back to local JSON if connection fails
@st.cache_data(ttl=600)  # 10 minute cache
def load_gsheets_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # Only select the columns we need
        data = conn.read(
            worksheet="DEVELOPMENT_PRODUCT_LIST",
            usecols=['Model', 'Length', 'Girth', 'Girth Category', 'Diameter', 'URL', 
                    'min_internal_length', 'max_internal_length_single_density',
                    'max_internal_length_double_density', 'max_internal_length_triple_zone_triple_density',
                    'max_internal_length_triple_zone'],
        )
        return data.to_dict(orient="records")
    except Exception as e:
        st.warning("Failed to load from Google Sheets, falling back to local data")
        with open('product_index.json') as f:
            return json.load(f)

# Process and cache sleeve data calculations, including recommended diameters and internal lengths based on sleeve type
@st.cache_data
def process_sleeve_data(data, user_diameter, selected_density):
    processed_data = []
    for obj in data.copy():  # Create copy to prevent modifying cached data
        obj['Recommended Diameter'] = get_recommended_opening_diameter(user_diameter, obj['Girth Category'])
        
        # Calculate supported densities based on internal length fields
        supported_densities = []
        
        # Helper function to check if a value is valid (not NaN, None, or empty string)
        def is_valid_value(value):
            if pd.isna(value) or value is None or value == '':
                return False
            return True
        
        # Check each density type with proper NaN/empty string handling
        if is_valid_value(obj.get('max_internal_length_single_density')):
            supported_densities.append("Single")
        if is_valid_value(obj.get('max_internal_length_double_density')):
            supported_densities.append("Dual")
        if is_valid_value(obj.get('max_internal_length_triple_zone')):
            supported_densities.append("Triple Zone")
        if is_valid_value(obj.get('max_internal_length_triple_zone_triple_density')):
            supported_densities.append("TDTZ")
            
        obj['Supported Densities'] = supported_densities
        
        # Set Max Internal Length based on selected density
        if selected_density == "Single" and is_valid_value(obj.get('max_internal_length_single_density')):
            obj['Max Internal Length'] = obj['max_internal_length_single_density']
        elif selected_density == "Dual" and is_valid_value(obj.get('max_internal_length_double_density')):
            obj['Max Internal Length'] = obj['max_internal_length_double_density']
        elif selected_density == "Triple Zone" and is_valid_value(obj.get('max_internal_length_triple_zone')):
            obj['Max Internal Length'] = obj['max_internal_length_triple_zone']
        elif selected_density == "TDTZ" and is_valid_value(obj.get('max_internal_length_triple_zone_triple_density')):
            obj['Max Internal Length'] = obj['max_internal_length_triple_zone_triple_density']
        else:
            # Fall back to old calculation method if selected density is not supported
            if 'girthy' in obj['Model'].lower():
                obj['Max Internal Length'] = obj['Length'] - 0.5
            elif 'curved' in obj['Girth Category'].lower():
                obj['Max Internal Length'] = obj['Length'] - 2
            elif 'prizefighter' in obj['Model'].lower():
                obj['Max Internal Length'] = 6.5
            else:
                obj['Max Internal Length'] = obj['Length'] - 1
            
        # Set Min Internal Length
        obj['Min Internal Length'] = obj.get('min_internal_length') if is_valid_value(obj.get('min_internal_length')) else 0
            
        processed_data.append(obj)
    return processed_data

# Get the pre-computed options
diameter_options, length_options = get_select_options()

col1, col2 = st.columns(2)
# Select fields for user inputs
with col1:
    # slider for diameter
    user_diameter = st.select_slider(
        "Erect Penis Diameter in Inches",
        diameter_options,
        help="Measure at the base, middle, and tip, then take the average"
    )
   
with col2:
    # user_length = st.selectbox("Penis Length in Inches", length_options)
    user_length = st.select_slider(
        "Erect Penis Length in Inches",
        length_options,
        help="Measure from base to tip, not pressing into the pubic bone"
    )

# Mapping of display labels to internal values for densities
density_label_to_value = {
    "Single Density": "Single",
    "Dual Density": "Dual",
    "Triple Zone": "Triple Zone",
    "TDTZ": "TDTZ"
}
density_labels = list(density_label_to_value.keys())
selected_label = st.radio(
    "Desired Sleeve Density",
    density_labels,
    index=0,  # Default to Single Density
    horizontal=True,  # Display radio buttons horizontally
    help="Select your preferred density. Products will be shown if they support the selected density."
)
selected_density = density_label_to_value[selected_label]

with st.expander("Advanced Filters"):
    # Slider for girth
    selected_girth = st.slider(
        "Min and Max Sleeve Girth",
        min_value=min([obj['Girth'] for obj in load_gsheets_data()]),
        max_value=max([obj['Girth'] for obj in load_gsheets_data()]),
        value=(min([obj['Girth'] for obj in load_gsheets_data()]), max([obj['Girth'] for obj in load_gsheets_data()]))  # default range
    )
    # Slider for Length
    selected_length = st.slider(
        "Min and Max Sleeve Length",
        min_value=min([obj['Length'] for obj in load_gsheets_data()]),
        max_value=max([obj['Length'] for obj in load_gsheets_data()]),
        value=(min([obj['Length'] for obj in load_gsheets_data()]), max([obj['Length'] for obj in load_gsheets_data()]))  # default range
    )

# Load and process data
with st.spinner('Loading products...'):
    raw_data = load_gsheets_data()
    data = process_sleeve_data(raw_data, user_diameter, selected_density)

# Calculate final girth when sleeve is worn, accounting for both internal diameter and sleeve wall thickness
def get_girth_when_worn(internal_diameter, sleeve_diameter):
    if internal_diameter == 'N/A':
        return 'N/A'
    else:
        # get shaft thickness 
        sleeve_thickness = sleeve_diameter - internal_diameter
        # get shaft + user diameter for total diameter
        total_diameter = sleeve_thickness + user_diameter
        # subtract 10% for compression
        squished_diameter = total_diameter * 0.9
        # convert diameter back to circumference
        total_circumference = (squished_diameter * math.pi) if squished_diameter >= sleeve_diameter else (sleeve_diameter * math.pi)
        # return the final worn circumference
        return round(total_circumference, 2)

# Round user length to nearest 0.5" increment to match standard sleeve sizing options
def round_user_length_to_nearest_half(number):
    # Multiply by 2, round down (floor), round to the closest whole number, then divide by 2
    return round(math.floor(number * 2)) / 2

# Recalculate the dynamic fields
for obj in data:
    internal_dimensions = f"{round_user_length_to_nearest_half(user_length)} x {obj['Recommended Diameter']}"
    obj['Recommended Internal Dimensions'] = internal_dimensions
    obj['Girth When Worn'] = get_girth_when_worn(obj['Recommended Diameter'], obj['Diameter'])

# Convert the updated data to a DataFrame
df = pd.DataFrame(data)

# Apply filters:
# 1. Filter rows where Length >= User Length
# 2. Filter rows where User Diameter < sleeve_external_diameter
# 3. Filter rows where recommended_diameter is not 'N/A'
# 4. Filter rows where the girth is >= the minimum girth
# 5. Filter rows where the girth is <= the maxmium girth
# 6. Filter rows where the length is >= the minimum length
# 7. Filter rows where the lenth is <= the maximum length
# 8. Filter rows where the selected density is supported
# 9. Filter rows where the user length is >= the minimum internal length
filtered_df = df[
    # BC recommendations
    (df['Max Internal Length'] >= user_length) & 
    (user_diameter < df['Diameter']) & 
    (df['Recommended Diameter'] != 'N/A') &
    # User filtering
    (df['Girth'] >= selected_girth[0]) &
    (df['Girth'] <= selected_girth[1]) &
    (df['Length'] >= selected_length[0]) &
    (df['Length'] <= selected_length[1]) &
    # Density filtering
    (df['Supported Densities'].apply(lambda x: selected_density in x)) &
    # Minimum internal length check
    (df['Min Internal Length'] <= user_length)
]

# show the header and count
header_text =f":green[{len(filtered_df)}] Compatible Sleeves"
st.header(header_text, help="The below sleeves fit your penis based on their available internal dimensions. Note: These are estimates, please verify the measurements before ordering on the Blissfull Creations website.")

# show toggle for additional columns
show_more = st.toggle("Show more detailed sleeve measurements")
# warning note
st.warning(":warning: Customizations such as density may impact the available internal dimensions of the sleeve. Please verify available dimensions on the Blissfull Creations website after selecting a product below.")

if show_more:
    displayed_column_order = [
        'Model',
        'URL',
        'Length', 
        'Min Internal Length',
        'Max Internal Length', 
        'Girth', 
        'Diameter', 
        'Girth Category',
        'Supported Densities',
        'Recommended Internal Dimensions', 
        'Girth When Worn'
    ]
else:
    displayed_column_order = [
        'Model',
        'URL',
        'Length', 
        'Girth',
        'Supported Densities',
        'Recommended Internal Dimensions', 
        'Girth When Worn'
    ]

# Display the filtered dataframe
if filtered_df.empty:
    st.warning("No compatible sleeves with the selected filters.")
else:
    columned_df = filtered_df[displayed_column_order]
    st.dataframe(
        columned_df, 
        column_config={
            "URL": st.column_config.LinkColumn(
                "Store Link",
                display_text="Link"
            ),
            "Recommended Internal Dimensions": "Rec. Internal Dimensions",
        },
        hide_index=True, 
        use_container_width=True
    )

# Footer
st.write('''
    Products Copyright [Blissfull Creations](https://blissfullcreations.com/).
''')