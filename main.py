import re

import matplotlib
import numpy as np

matplotlib.use('Agg')

import requests
import plotly.express as px
import pandas as pd

import plotly.graph_objs as go


pd.set_option('display.min_rows', 100)
pd.set_option('display.max_rows', 150)
pd.set_option('display.max_columns', 13)
pd.set_option('display.width', 2000)


def fetch_artworks():
    url = "https://collectionapi.metmuseum.org/public/collection/v1/objects"
    params = {"departmentIds": [17]}  # ID for the Medieval Art department
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()["objectIDs"]
    else:
        return None


def fetch_artwork_details(object_id):
    url = f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{object_id}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return {
            "objectID": object_id,
            "title": data.get("title"),
            "artist": data.get("artistDisplayName"),
            "year": data.get("objectDate"),
            "region": data.get("artistDisplayBio"),
        }
    else:
        return None


def contains_integer(input_string):
    integer_pattern = r'\d+'
    match = re.search(integer_pattern, input_string)
    return match is not None


columns_to_keep = ['Object Number', 'Title', 'Object Date',
                   'Culture', 'Medium']

met_data = pd.read_csv("openaccess/met.csv")

medieval_art = met_data[met_data['Department'] == 'Medieval Art'].copy()
medieval_art['Object Begin Date'] = pd.to_numeric(medieval_art['Object Begin Date'], errors='coerce')
medieval_art = medieval_art[columns_to_keep]
art_df = medieval_art.copy()

print(art_df)
print(art_df["Object Date"])
# print(art_df["Object Date"].to_string(index=False))


# Function to convert century text to year
def century_to_year(century_str, part_of_century='', is_bce=False):
    try:
        century = int(''.join(filter(str.isdigit, century_str)))
    except ValueError:
        raise ValueError(f"Cannot extract century from '{century_str}'")

    year_start = (century - 1) * 100
    year_end = century * 100

    if is_bce:
        year_start, year_end = -year_end, -year_start

    # Adjust for early, mid, and late
    if part_of_century == 'early':
        return year_start, year_start + 33
    elif part_of_century == 'mid':
        return year_start + 34, year_start + 66
    elif part_of_century == 'late':
        return year_start + 67, year_end
    else:
        return year_start, year_end


# Function to parse a date range string
def parse_date_range(date_range):
    # Normalize the string (remove 'ca.', 'or later', 'or modern', etc.)
    normalized_range = date_range.lower().split(' or ')[0]
    if not contains_integer(normalized_range):
        normalized_range = date_range.lower().split(' or ')[1]

    parts = normalized_range.replace('ca. ', '').replace('s', '').split('–')
    start_part, end_part = (parts + parts)[:2]  # Handles single entry cases

    is_bce = 'bce' in start_part or 'bce' in end_part
    part_of_century_start = 'early' if 'early' in start_part else 'mid' if 'mid' in start_part else 'late' if 'late' in start_part else ''
    part_of_century_end = 'early' if 'early' in end_part else 'mid' if 'mid' in end_part else 'late' if 'late' in end_part else ''

    # Logic for 'mid' or 'third quarter'
    def interpret_complex_phrase(part):
        if 'mid' in part:
            return 'mid'
        if 'third quarter' in part:
            return 'third quarter'
        return ''

    complex_phrase_start = interpret_complex_phrase(start_part)
    complex_phrase_end = interpret_complex_phrase(end_part)

    # Extract numeric part from century strings, if available
    start_century = ''.join(filter(str.isdigit, start_part))
    end_century = ''.join(filter(str.isdigit, end_part))

    try:
        if complex_phrase_start or complex_phrase_end:
            # Handle complex phrases
            century = int(start_century or end_century)
            if complex_phrase_start == 'mid':
                start = (century - 1) * 100 + 34
            elif complex_phrase_start == 'third quarter':
                start = (century - 1) * 100 + 50
            else:
                start = (century - 1) * 100

            if complex_phrase_end == 'mid':
                end = (century - 1) * 100 + 66
            elif complex_phrase_end == 'third quarter':
                end = (century - 1) * 100 + 75
            else:
                end = century * 100
        else:
            # Handle normal cases
            start = century_to_year(start_century, part_of_century_start, is_bce)
            end = century_to_year(end_century, part_of_century_end, is_bce)
    except ValueError as e:
        raise ValueError(f"{e}, \ndate_range: {date_range}, start_century: {start_century}, end_century: {end_century}")

    try:
        return start, end
    except:
        pass


def normalize_year(year):
    if isinstance(year, tuple):
        return year[0]  # Assuming the first element of the tuple is the start year
    return year


art_df = art_df[art_df["Object Date"].notna()]
parsed_ranges = [parse_date_range(dr) for dr in art_df["Object Date"].astype(str)]
starts, ends = zip(*parsed_ranges)

art_df['Start Year'], art_df['End Year'] = zip(*parsed_ranges)

# Normalize years
art_df['Start Year'] = art_df['Start Year'].apply(normalize_year)
art_df['End Year'] = art_df['End Year'].apply(normalize_year)

# Prepare heatmap data
year_min, year_max = art_df['Start Year'].min(), art_df['End Year'].max()
heatmap_data = np.zeros(year_max - year_min + 1)


new_df = art_df.head(50)

df = art_df[(art_df['Start Year'] >= 200) & (art_df['Start Year'] <= 2000)]
df = df[(df['End Year'] >= 200) & (df['End Year'] <= 2000)]


# Assuming you have your dataset in a pandas DataFrame called 'df'
start_years = df['Start Year']
end_years = df['End Year']
mediums = df['Medium']
cultures = df['Culture']

# Create a figure with four subplots
fig, ((ax3, ax4), (ax1, ax2)) = plt.subplots(2, 2, figsize=(12, 15))

# Plot the Start Year histogram
ax1.hist(start_years, bins=20, edgecolor='k')
ax1.set_title('Distribution of Start Years')
ax1.set_xlabel('Start Year')
ax1.set_ylabel('Frequency')
ax1.grid(axis='y', alpha=0.75)

# Plot the End Year histogram
ax2.hist(end_years, bins=20, edgecolor='k', color='orange')  # You can adjust the number of bins as needed
ax2.set_title('Distribution of End Years')
ax2.set_xlabel('End Year')
ax2.set_ylabel('Frequency')
ax2.grid(axis='y', alpha=0.75)

# Plot the Medium bar chart
medium_counts = mediums.value_counts().head(10)  # You can adjust the number of categories to display
medium_counts.plot(kind='bar', ax=ax3)
ax3.set_title('Top 10 Mediums')
ax3.set_xlabel('Medium')
ax3.set_ylabel('Count')
ax3.grid(axis='y', alpha=0.75)

# Plot the Culture bar chart
culture_counts = cultures.value_counts().head(10)  # You can adjust the number of categories to display
culture_counts.plot(kind='bar', ax=ax4)
ax4.set_title('Top 10 Cultures')
ax4.set_xlabel('Culture')
ax4.set_ylabel('Count')
ax4.grid(axis='y', alpha=0.75)

plt.subplots_adjust(hspace=0.9)

# Save the plot to a file
plt.savefig('year_medium_culture_visualization.png')

