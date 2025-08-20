# BMHC Quarter 4 2024

### Welcome to the Black Men's Health Clinic Q4 2024 Data Report. This project involves analyzing data collected from various service interactions and aims to provide insights into the services provided, demographic information, and other relevant data points to improve service delivery and outcomes.

#### The dataset includes the following columns:

- Personal submitting this form? (object): 
  - The individual who submitted the form.
- Date (datetime64[ns]): 
  - The date of the service interaction.
- Coverage (object): 
  - Type of coverage provided.
- Gender (object): 
  - Gender of the individual.
- Service (object): 
  - Type of service provided.
- Housing (object): 
  - Housing status of the individual.
- Zip Code (int64): 
  - Zip code of the individual.
- First Name (object): 
  - First name of the individual.
- Last Name (object): 
  - Last name of the individual.
- Age (int64): 
  - Age of the individual.
- Communication Type: 
  - Type of communication used (object).
- Physical Appointment (object): 
  - Whether a physical appointment was made.
- BMHC Referrals (object): 
  - Referrals to BMHC.
- Mental Health (object): 
  - Mental health status.
- Health Specialist (float64): 
  - Involvement of a health specialist.
- Transportation (object): 
  - Transportation needs.
- Diversion (object): 
  - Diversion services provided.
- Income (object): 
  - Income level of the individual .
- Race/Ethnicity (object): 
  - Race or ethnicity of the individual.

## The Dataset

Below is the imported data that we will be using for this report:

```bash
import os
import pandas as pd

current_dir = os.getcwd()
script_dir = os.path.dirname(os.path.abspath(__file__))
data_path = 'data/bmhc_data_2024.xlsx'
file_path = os.path.join(script_dir, data_path)
q4_bmhc = 'Q4_BMHC'
q4_fh = 'Q4_FH'
data1 = pd.read_excel(file_path, sheet_name=q4_bmhc)
data2 = pd.read_excel(file_path, sheet_name=q4_fh)
df = data1.copy()
df = data2.copy()
```