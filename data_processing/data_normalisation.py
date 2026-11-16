# Generated from: data_normalisation.ipynb
# Converted at: 2026-09-03T10:24:40.299Z
# Next step (optional): refactor into modules & generate tests with RunCell
# Quick start: pip install runcell

import pandas as pd

# Read the joined data
joined_data = pd.read_csv("joined_data.csv")

print("Total records:", len(joined_data))
print("\nColumn names:")
print(joined_data.columns.tolist())

print("\nFirst five rows:")
print(joined_data.head())

# Create the Location table
location = joined_data[
    [
        "LGA code",
        "LGA name",
        "S/T code",
        "S/T name"
    ]
].drop_duplicates().copy()

# Rename the columns
location.columns = [
    "lga_code",
    "lga_name",
    "state_code",
    "state_name"
]

# Reset the row index
location = location.reset_index(drop=True)

print("\nLocation table:")
print(location.head())

print("\nTotal locations:", len(location))

# Create the Demographic table
demographic = joined_data[
    [
        "Sex",
        "Age group",
        "Prevalence per 1000"
    ]
].drop_duplicates().copy()

# Reset the row index
demographic = demographic.reset_index(drop=True)

# Create the demographic ID
demographic.insert(
    0,
    "demo_id",
    range(1, len(demographic) + 1)
)

print("\nDemographic table:")
print(demographic)

print("\nTotal demographic groups:", len(demographic))

# Rename the Demographic columns
demographic = demographic.rename(
    columns={
        "Sex": "sex",
        "Age group": "age_group",
        "Prevalence per 1000": "prevalence_per_1000"
    }
)

print("\nFinal Demographic table:")
print(demographic)

print("LEFT:", joined_data.columns.tolist())
print("RIGHT:", demographic.columns.tolist())

fact_data = pd.merge(
    joined_data,
    demographic,
    left_on=["Sex", "Age group"],
    right_on=["sex", "age_group"],
    how="left"
)

print("\nMerged data:")
print(fact_data.head())

# Create the Estimate fact table
estimate = fact_data[
    [
        "LGA code",
        "demo_id",
        "Population",
        "Modelled estimate"
    ]
].copy()

# Rename the columns
estimate.columns = [
    "lga_code",
    "demo_id",
    "population",
    "modelled_estimate"
]

print("\nEstimate table:")
print(estimate.head())

print("\nTotal estimates:", len(estimate))

# Check duplicated primary keys
print("\nDuplicated location IDs:")
print(location["lga_code"].duplicated().sum())

print("\nDuplicated demographic IDs:")
print(demographic["demo_id"].duplicated().sum())

# Check missing foreign keys
print("\nMissing LGA codes in Estimate:")
print(estimate["lga_code"].isnull().sum())

print("\nMissing demographic IDs in Estimate:")
print(estimate["demo_id"].isnull().sum())

# Check duplicated fact records
print("\nDuplicated LGA and demographic combinations:")
print(
    estimate.duplicated(
        subset=["lga_code", "demo_id"]
    ).sum()
)

# Save the three normalised tables
location.to_csv(
    "location.csv",
    index=False
)

demographic.to_csv(
    "demographic.csv",
    index=False
)

estimate.to_csv(
    "estimate.csv",
    index=False
)

print("\nThree CSV files saved successfully:")
print("location.csv")
print("demographic.csv")
print("estimate.csv")

# Round modelled estimates to five decimal places
estimate["modelled_estimate"] = (
    estimate["modelled_estimate"].round(5)
)

# Save the updated Estimate table
estimate.to_csv(
    "estimate.csv",
    index=False
)