# Generated from: data_cleaning.ipynb
# Converted at: 2026-09-03T10:24:52.550Z
# Next step (optional): refactor into modules & generate tests with RunCell
# Quick start: pip install runcell

import pandas as pd
# Path to the original ABS dataset
file_path = (
     "ABS 2025 LGA.xlsx"
)

# open the excel workbook
abs_excel = pd.ExcelFile(file_path)

# display all worksheet names
print("Worksheets in the ABS file:")
print(abs_excel.sheet_names)

# Import the male and female population worksheets
male_data = pd.read_excel(
    file_path,
    sheet_name="Table 1",
    header=None
)
female_data = pd.read_excel(
    file_path,
    sheet_name="Table 2",
    header=None
)

# Display the number of rows and columns
print("\nTable 1 shape:")
print(male_data.shape)

print("\nTable 2 shape:")
print(female_data.shape)

# Display the first 10 rows
print("\nFirst 10 rows of Table 1:")
print(male_data.head(10))

print("\nFirst 10 rows of Table 2:")
print(female_data.head(10))

# Extract the data required for Iteration 1
# Read Table 1 using the age-group row as the header
male_extract = pd.read_excel(
    file_path,
    sheet_name= "Table 1",
    header=4,
    usecols= "A:V"
)

# Read Table 2 using the age-group row as the header
female_extract = pd.read_excel(
    file_path,
    sheet_name= "Table 2",
    header=4,
    usecols= "A:V"
)

# Standardise the column names
male_extract.columns = [
    str(column).strip().replace("–", "-")
    for column in male_extract.columns
]

female_extract.columns = [
    str(column).strip().replace("–", "-")
    for column in female_extract.columns
]

# Rename the first four columns
male_extract.columns.values[0] = "S/T code"
male_extract.columns.values[1] = "S/T name"
male_extract.columns.values[2] = "LGA code"
male_extract.columns.values[3] = "LGA name"

female_extract.columns.values[0] = "S/T code"
female_extract.columns.values[1] = "S/T name"
female_extract.columns.values[2] = "LGA code"
female_extract.columns.values[3] = "LGA name"

# Remove the extra unit row below the headings
male_extract = male_extract.iloc[1:]
female_extract = female_extract.iloc[1:]

# Keep only Victorian records
male_victoria = male_extract[
    male_extract["S/T name"] == "Victoria"
].copy()

female_victoria = female_extract[
    female_extract["S/T name"] == "Victoria"
].copy()

# Select the columns required for Iteration 1
selected_columns = [
    "S/T code",
    "S/T name",
    "LGA code",
    "LGA name",
    "30-34",
    "35-39",
    "40-44",
    "45-49",
    "50-54",
    "55-59",
    "60-64",
    "65-69",
    "70-74",
    "75-79",
    "80-84",
    "85 and over"
]

# Apply the column selection
male_victoria = male_victoria[selected_columns].copy()
female_victoria= female_victoria[selected_columns].copy()

# Add the sex classification
male_victoria["Sex"] = "Male"
female_victoria["Sex"] = "Female"

# Combine the male and female records
abs_extracted = pd.concat(
    [male_victoria, female_victoria],
    ignore_index= True
)

# Display the extraction result
print("Male Victorian records", len(male_victoria))
print("Female Victorian records", len(female_victoria))
print("Total extracted records:", len(abs_extracted))

print("\nFirst five extracted rows:")
print(abs_extracted.head())

print("-Data Quality Check-")
# Check missing values
print("\nMissing values in each column:")
print(abs_extracted.isnull().sum())

# Check completely duplicated rows
duplicate_rows = abs_extracted.duplicated().sum()
print("\nNumber of duplicated rows:")
print(duplicate_rows)

# Check duplicated LGA and sex combinations
duplicate_lga_sex = abs_extracted.duplicated(
    subset = ["LGA code", "Sex"]
).sum()
print("\nNumber of duplicated LGA and sex combinations:")
print(duplicate_lga_sex)

# Check data type
print("\nData types:")
print(abs_extracted.dtypes)

# Import the AIHW dataset

aihw_file_path = (
    "AIHW dementia prevalence rates.xlsx"
)

# open the excel workbook
aihw_excel = pd.ExcelFile(aihw_file_path)

# display all worksheet names
print("Worksheets in the AIHW file:")
print(aihw_excel.sheet_names)

# Read the AIHW prevalence table without setting a header
aihw_raw = pd.read_excel(
    aihw_file_path,
    sheet_name= "S2.1",
    header= None
)

# Display the size of the worksheet
print("\nAIHW worksheet shape:")
print(aihw_raw.shape)

# Display the first 25 rows 
print("\nFirst 25 rows of the AIHW worksheet:")
print(aihw_raw.head(25).to_string)

# Extract the AIHW data required for Iteration 1

# Select Sex, Age group and the 2025 prevalence rate

aihw_extracted = aihw_raw.iloc[4:,[0,1,3]].copy()

#Rename the columns
aihw_extracted.columns = [
    "Sex",
    "Age group",
    "Prevalence per 1000"
]

# Fill the blank sex cells with the previous sex value
aihw_extracted["Sex"] = aihw_extracted["Sex"].ffill()

# Standardise the text values
aihw_extracted["Sex"] = (
    aihw_extracted["Sex"].astype(str).str.strip()
)

# Replace long dashes with standard hyphens in age groups
aihw_extracted["Age group"] = (
    aihw_extracted["Age group"].astype(str).str.strip().str.replace("–", "-", regex=False)
)
#Age groups required for the calculation
selected_age_groups = [
     "30-59",
     "60-64",
     "65-69",
     "70-74",
     "75-79",
     "80-84",
     "85-89",
     "90+"
]

# Keep only Men and Women with detailed age groups
aihw_extracted = aihw_extracted[
    (aihw_extracted["Sex"].isin(["Men","Women"])) &
    (aihw_extracted["Age group"].isin(selected_age_groups))
].copy()

# Match the sex lables used in the ABS dataset
aihw_extracted["Sex"] = aihw_extracted["Sex"].replace({
    "Men": "Male",
    "Women": "Female"
})

#Convert prevalence rates to number
aihw_extracted["Prevalence per 1000"] = pd.to_numeric(
    aihw_extracted["Prevalence per 1000"],
    errors= "coerce"
)

# Reset the row index
aihw_extracted = aihw_extracted.reset_index(drop= True)

# Display the extraction result

print("\nAIHW Extraction Result")
print("Total extracted records:", len(aihw_extracted))


print("\nExtracted AIHW data")
print(aihw_extracted.to_string(index= False))

# Check missing values
print("\nMissing values:")
print(aihw_extracted.isnull().sum())

# Check duplicated Sex and Age group combinations
duplicate_aihw = aihw_extracted.duplicated(
    subset= ["Sex", "Age group"]
).sum()

print("\nDuplicated Sex and Age group combinations:")
print(duplicate_aihw)

# Check zero or negative prevalence rates
invalid_rates = (
    aihw_extracted["Prevalence per 1000"] <=0
).sum()

print("\nInvalid prevalence rates:")
print(invalid_rates)

# Display data types
print("\nData types:")
print(aihw_extracted.dtypes)

# Prepare the ABS data for joining

# Create a copy of the extracted ABS data
abs_ready = abs_extracted.copy()

# Remove the unincorporated area
abs_ready = abs_ready[
    abs_ready["LGA name"] != "Unincorporated Vic"
].copy()

# ABS age columns
abs_age_columns = [
    "30-34",
    "35-39",
    "40-44",
    "45-49",
    "50-54",
    "55-59",
    "60-64",
    "65-69",
    "70-74",
    "75-79",
    "80-84",
    "85 and over"
]

# Convert population values to numbers
for column in abs_age_columns:
    abs_ready[column] = pd.to_numeric(
        abs_ready[column],
        errors="coerce"
    )

# Add the population aged from 30 to 59
abs_ready["30-59"] = (
    abs_ready["30-34"]
    + abs_ready["35-39"]
    + abs_ready["40-44"]
    + abs_ready["45-49"]
    + abs_ready["50-54"]
    + abs_ready["55-59"]
)

# Rename the oldest age group
abs_ready = abs_ready.rename(
    columns={"85 and over": "85+"}
)

# Age groups shared by ABS and AIHW
age_groups = [
    "30-59",
    "60-64",
    "65-69",
    "70-74",
    "75-79",
    "80-84",
    "85+"
]

# Keep only the required columns
abs_ready = abs_ready[
    [
        "S/T code",
        "S/T name",
        "LGA code",
        "LGA name",
        "Sex"
    ] + age_groups
].copy()

print("\nABS data ready:")
print(abs_ready.head())
print("Total ABS records:", len(abs_ready))



# Convert the ABS data to long format

abs_long = pd.melt(
    abs_ready,
    id_vars=[
        "S/T code",
        "S/T name",
        "LGA code",
        "LGA name",
        "Sex"
    ],
    value_vars=age_groups,
    var_name="Age group",
    value_name="Population"
)

print("\nABS long-format data:")
print(abs_long.head(10).to_string(index=False))

print("\nTotal ABS long-format records:")
print(len(abs_long))


# Join the ABS and AIHW data

joined_data = pd.merge(
    abs_long,
    aihw_extracted,
    on=["Sex", "Age group"],
    how="left"
)

print("\nJoined data:")
print(joined_data.head(10).to_string(index=False))

print("\nTotal joined records:")
print(len(joined_data))

# Check the join result


print("\nMissing values:")
print(joined_data.isnull().sum())

unmatched_records = joined_data[
    joined_data["Prevalence per 1000"].isnull()
]

print("\nUnmatched records:")
print(len(unmatched_records))

print("ABS sex values:")
print(abs_long["Sex"].unique())

print("\nAIHW sex values:")
print(aihw_extracted["Sex"].unique())

print("\nABS age groups:")
print(abs_long["Age group"].unique())

print("\nAIHW age groups:")
print(aihw_extracted["Age group"].unique())

# Validate the AIHW 85+ prevalence rate

# Select the 2025 estimated number and prevalence rate
aihw_validation = aihw_raw.iloc[4:, [0, 1, 2, 3]].copy()

# Rename the columns
aihw_validation.columns = [
    "Sex",
    "Age group",
    "Estimated number",
    "Prevalence per 1000"
]

# Fill blank sex cells
aihw_validation["Sex"] = aihw_validation["Sex"].ffill()

# Standardise text values
aihw_validation["Sex"] = (
    aihw_validation["Sex"]
    .astype(str)
    .str.strip()
)

aihw_validation["Age group"] = (
    aihw_validation["Age group"]
    .astype(str)
    .str.strip()
    .str.replace("–", "-", regex=False)
)


# Keep only Men, Women, 85-89 and 90+
aihw_validation = aihw_validation[
    (aihw_validation["Sex"].isin(["Men", "Women"])) &
    (aihw_validation["Age group"].isin(["85-89", "90+"]))
].copy()


# Convert estimated numbers to numeric values
aihw_validation["Estimated number"] = pd.to_numeric(
    aihw_validation["Estimated number"],
    errors="coerce"
)

aihw_validation["Prevalence per 1000"] = pd.to_numeric(
    aihw_validation["Prevalence per 1000"],
    errors="coerce"
)

# Estimate the population used by AIHW
aihw_validation["Estimated population"] = (
    aihw_validation["Estimated number"]
    / aihw_validation["Prevalence per 1000"]
    * 1000
)

# Calculate the combined 85+ rate for each sex
calculated_85_plus = aihw_validation.groupby(
    "Sex",
    as_index=False
).agg({
    "Estimated number": "sum",
    "Estimated population": "sum"
})

calculated_85_plus["Calculated 85+ rate"] = (
    calculated_85_plus["Estimated number"]
    / calculated_85_plus["Estimated population"]
    * 1000
)

print("\nCalculated 85+ rates:")
print(calculated_85_plus.to_string(index=False))

# Prepare the final AIHW data for joining

# Select Sex, Age group and the official 2025 prevalence rate
aihw_final = aihw_raw.iloc[4:, [0, 1, 3]].copy()

# Rename the columns
aihw_final.columns = [
    "Sex",
    "Age group",
    "Prevalence per 1000"
]

# Fill blank sex cells
aihw_final["Sex"] = aihw_final["Sex"].ffill()

# Clean the text values
aihw_final["Sex"] = (
    aihw_final["Sex"]
    .astype(str)
    .str.strip()
)

aihw_final["Age group"] = (
    aihw_final["Age group"]
    .astype(str)
    .str.strip()
    .str.replace("–", "-", regex=False)
)

# Keep the age groups that match the ABS data
age_groups = [
    "30-59",
    "60-64",
    "65-69",
    "70-74",
    "75-79",
    "80-84",
    "85+"
]

aihw_final = aihw_final[
    (aihw_final["Sex"].isin(["Men", "Women"])) &
    (aihw_final["Age group"].isin(age_groups))
].copy()

# Match the ABS sex labels
aihw_final["Sex"] = aihw_final["Sex"].replace({
    "Men": "Male",
    "Women": "Female"
})

# Convert prevalence rates to numbers
aihw_final["Prevalence per 1000"] = pd.to_numeric(
    aihw_final["Prevalence per 1000"],
    errors="coerce"
)

# Reset the row index
aihw_final = aihw_final.reset_index(drop=True)

print("\nFinal AIHW data:")
print(aihw_final.to_string(index=False))
print("\nTotal AIHW records:", len(aihw_final))

# Join the ABS and AIHW data

joined_data = pd.merge(
    abs_long,
    aihw_final,
    on=["Sex", "Age group"],
    how="left"
)

print("\nJoined data:")
print(joined_data.head(10).to_string(index=False))

print("\nTotal joined records:", len(joined_data))

print(
    "\nUnmatched records:",
    joined_data["Prevalence per 1000"].isnull().sum()
)

# Calculate the modelled estimate

joined_data["Modelled estimate"] = (
    joined_data["Population"]
    * joined_data["Prevalence per 1000"]
    / 1000
)

print("\nCalculation result:")
print(
    joined_data[
        [
            "LGA name",
            "Sex",
            "Age group",
            "Population",
            "Prevalence per 1000",
            "Modelled estimate"
        ]
    ].head(10).to_string(index=False)
)

# Calculate the total estimate for each LGA

lga_estimates = joined_data.groupby(
    ["LGA code", "LGA name"],
    as_index=False
)["Modelled estimate"].sum()

# Round only the final LGA result
lga_estimates["Rounded estimate"] = (
    lga_estimates["Modelled estimate"].round()
)

print("\nLGA modelled estimates:")
print(lga_estimates.to_string(index=False))

print("\nTotal LGAs:", len(lga_estimates))

# Rename the column headers
lga_estimates = lga_estimates.rename(
    columns={
        "LGA code": "lga_code",
        "LGA name": "lga_name",
        "Modelled estimate": "modelled_estimate",
        "Rounded estimate": "rounded_estimate"
    }
)

# Save the final data to CSV
output_file = "lga_modelled_estimates.csv"

lga_estimates.to_csv(
    output_file,
    index=False
)

print("\nCSV file saved successfully:")
print(output_file)

print("\nColumn headers:")
print(lga_estimates.columns.tolist())

# Save the joined data for normalisation
joined_data.to_csv(
    "joined_data.csv",
    index=False
)

print("joined_data.csv saved successfully.")