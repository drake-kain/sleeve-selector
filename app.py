import streamlit as st
import pandas as pd
import json
import math
from streamlit_gsheets import GSheetsConnection

# Helper function to generate floating point ranges
def frange(start, stop, step):
    while start < stop:
        yield start
        start += step

# Function to normalize the category name
def normalize_category(category_name):
    return category_name.lower().strip() if category_name else category_name

# Function to get the recommended opening diameter based on user diameter and category
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

# page configurations
st.set_page_config(
    page_title="Sleeve Selector",
    page_icon="🍆",
    # layout="wide",
    menu_items={
        'Report a bug': "https://www.reddit.com/message/compose/?to=drake_kain",
        'About': f"""
        Input your length and diameter to show compatible sleeves. A compatible sleeve
        has a total diameter larger than you, a max interior length as long as you, and an opening
        small enough or large enough to give you a proper, snug fit.
                
        We will also show the total girth of the sleeve when worn with the recommended diameter.
        No more guesswork when comparing models!
        
        Made by [/u/drake_kain](https://www.reddit.com/user/drake_kain/)"""
    }
)

# Title 
st.title('Sleeve Selector :eggplant:')
st.info(''' 
        Find the perfect sleeve and fit according to Blissfull Creation's [How to Order](https://blissfullcreations.com/pages/how-to-order?hash=U2FsdGVkX18ktvbAO4N2cENwuIXMnPrUuO8ciYPKC52hXSg2iTHGmKDIGyPC1WGNMLFPIPgJvIMjr0KRkdhCgPF9+IdbosGELowyqQau4gN32mnpbFutimq4JqLM+CRSFJqd5Uq8GnGBVLKEAvB8qw==) guide. 
          
        Select your penis dimensions below to find compatible sized sleeves, while also being provided
        a Recommended Internal Dimensions for ordering.
    ''')

# Cache the function that loads the JSON file
@st.cache_data
def load_json_data(file_path):
    with open(file_path) as f:
        return json.load(f)
    
# Cache the function that loads the Google Sheets file
@st.cache_data
def load_gsheets_data():
    # try and load google sheets data first, if it fails, go to the local json
    try:
        # Reference the connection from the secrets.toml
        conn = st.connection("gsheets", type=GSheetsConnection)
        # from the gsheet, only pull in the production product list tab
        data = conn.read(
            worksheet="PRODUCTION_PRODUCT_LIST",
            # set the cache to 10 min
            ttl="10m"
        )
        # convert the dataframe to a dictionary for modifying and manipulating data
        object_data = data.to_dict(orient="records")
    except:
        # if google sheets fails, fall back to local json file
        object_data = load_json_data('product_index.json')
    finally:
        # return the python object version of the datas
        return object_data

# Load the product data
with st.spinner('Loading products...'):
    data = load_gsheets_data();

# Create options for select boxes
diameter_options = [round(x, 3) for x in list(frange(1, 3.125, 0.125))]
length_options = [round(x, 2) for x in list(frange(3, 9.25, 0.25))]

@st.cache_data
def get_min_and_max_values(data):
    # Initialize variables for min and max values
    min_length = float('inf')
    max_length = float('-inf')
    min_girth = float('inf')
    max_girth = float('-inf')
    
    # Loop through each object in the JSON array
    for obj in data:
        length = float(obj["Length"])  # Convert to float for consistency
        girth = float(obj["Girth"])  # Convert to float for consistency

        # Update min and max values for Length
        if length < min_length:
            min_length = length
        if length > max_length:
            max_length = length

        # Update min and max values for Girth
        if girth < min_girth:
            min_girth = girth
        if girth > max_girth:
            max_girth = girth
            
    return {
        'min_length': min_length,
        'max_length': max_length,
        'min_girth': min_girth,
        'max_girth': max_girth
    }

# get the min and max values
min_max_data = get_min_and_max_values(data)

col1, col2 = st.columns(2)
# Select fields for user inputs
with col1:
    # slider for diameter
    # user_diameter = st.selectbox("Penis Diameter in Inches", diameter_options)
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

with st.expander("Advanced Filters"):
    # Slider for girth
    selected_girth = st.slider(
        "Min and Max Sleeve Girth",
        min_value=min_max_data['min_girth'],
        max_value=min_max_data['max_girth'],
        value=(min_max_data['min_girth'], min_max_data['max_girth']),  # default range
    )
    # Slider for Length
    selected_length = st.slider(
        "Min and Max Sleeve Length",
        min_value=min_max_data['min_length'],
        max_value=min_max_data['max_length'],
        value=(min_max_data['min_length'], min_max_data['max_length'])  # default range
    )
    
# Add new keys to each object in the JSON array, do this once and cache it
@st.cache_data
def add_calculated_fields(data):
  for obj in data:
    # Adjust Max Internal Lengths for specific sleeves
    # Girthy boy only requires 0.5" lower than total length
    if 'girthy' in obj['Model'].lower():
        obj['Max Internal Length'] = obj['Length'] - 0.5
    # Curved sleeves (Lova Lova) require 2 inches between insertable and total length
    elif 'curved' in obj['Girth Category'].lower():
        obj['Max Internal Length'] = obj['Length'] - 2
    # prize fighter is a special curved, with max internal of 6.5 inches
    elif 'prizefighter' in obj['Model'].lower():
        obj['Max Internal Length'] = 6.5
    # default for all other sleeves is 1 inch of space, exceptions for dual/triple density
    else:
        obj['Max Internal Length'] = obj['Length'] - 1
  return data

# calcuate new fields
data = add_calculated_fields(data)

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

def round_user_length_to_nearest_half(number):
    # Multiply by 2, round down (floor), round to the closest whole number, then divide by 2
    return round(math.floor(number * 2)) / 2

# Recalculate the dynamic fields
for obj in data:
    # Calculate recommended_diameter based on the selected user_diameter and object's Girth Category
    obj['Recommended Diameter'] = get_recommended_opening_diameter(user_diameter, obj['Girth Category'])
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
filtered_df = df[
    # BC recommendations
    (df['Max Internal Length'] >= user_length) & 
    (user_diameter < df['Diameter']) & 
    (df['Recommended Diameter'] != 'N/A') &
    # User filtering
    (df['Girth'] >= selected_girth[0]) &
    (df['Girth'] <= selected_girth[1]) &
    (df['Length'] >= selected_length[0]) &
    (df['Length'] <= selected_length[1]) 
]

# show the header and count
header_text =f":green[{len(filtered_df)}] Compatible Sleeves"
st.header(header_text, help="The below sleeves fit your penis based on their available internal dimensions")

# show toggle for additional columns
show_more = st.toggle("Show more detailed sleeve measurements")

if show_more:
    displayed_column_order = [
        'Model',
        'URL',
        'Length', 
        'Max Internal Length', 
        'Girth', 
        'Diameter', 
        'Girth Category', 
        'Recommended Internal Dimensions', 
        'Girth When Worn'
    ]
else:
    displayed_column_order = [
        'Model',
        'URL',
        'Length', 
        'Girth', 
        'Recommended Internal Dimensions', 
        'Girth When Worn'
    ]

# Display the filtered dataframe
if filtered_df.empty:
    st.warning("No compatible sleeves with the selected filters.")
else:
    st.dataframe(
        filtered_df, 
        column_config={
            "URL": st.column_config.LinkColumn(
                "Store Link",
                display_text="Link"
            )
        },
        hide_index=True, 
        use_container_width=True,
        column_order=displayed_column_order
    )


# Footer
st.write('''
    Products Copyright [Blissfull Creations](https://inviteee.to/i/uEvPz). Have feedback? [Submit it!](https://www.reddit.com/message/compose/?to=drake_kain)
''')