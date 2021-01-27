import streamlit as st
import pandas as pd
import altair as alt


def clean_summary_data(file_str:str, name:str):
     
    input_df = pd.read_csv(
        file_str,
        names=['1', '2','3','type','ministry','source','amount'],
        thousands=',') 
    input_df[['amount']] = input_df[['amount']].fillna(value='EMPTY')
    input_df = (input_df.fillna(method='ffill') # populate columns with previous value
                        .drop(['1','2'], axis=1) # drop unused columns
                        .drop([0,1,2,3,]) # drop first ununsed rows
            )

    # remove other income / expenses
    input_df.drop(input_df[input_df['3'] == 'Other Expense'].index, inplace = True) 
    input_df.drop(input_df[input_df['3'] == 'Other Income'].index, inplace = True) 
    input_df.drop(input_df[input_df['3'] == 'Total Other Income'].index, inplace = True) 
    input_df.drop(input_df[input_df['3'] == 'Total Other Expense'].index, inplace = True)
    input_df = input_df.drop(['3'], axis=1)

    # exclude Transfer from Invested Funds
    # input_df.drop(input_df[input_df['source'] == 'Transfer from Invested Funds'].index, inplace = True)
    # input_df.drop(input_df[input_df['source'] == 'Endowment Fund earnings'].index, inplace = True)
    # input_df.drop(input_df[input_df['source'] == 'Endowment Fund earnings'].index, inplace = True)

    # remove summary income fields
    # input_df.drop(input_df[input_df['ministry'] == 'Transfer from Invested Funds'].index, inplace = True)
    input_df.drop(input_df[input_df['ministry'].str.startswith('Total')].index, inplace = True)
    input_df.drop(input_df[input_df['type'].str.startswith('Total')].index, inplace = True)
    input_df.drop(input_df[input_df['amount'] == 'EMPTY'].index, inplace = True)

    # set all amount types to float
    input_df['amount'] = input_df['amount'].astype(float)
    # input_df = input_df.set_index(['type','ministry', 'source'])
    input_df.set_index(['type','ministry','source'])
    input_df = input_df.rename(columns={'amount': name})

    # Caputre Guest Pastors
    guest_pastors_loc = input_df.index[input_df['ministry'] == 'Guest Pastors'].tolist()
    if guest_pastors_loc:
        input_df.loc[guest_pastors_loc[0], 'source'] = 'Guest Pastors'
        input_df.loc[guest_pastors_loc[0], 'ministry'] = 'Pastoral Ministry'
    
    # Capture Severance Pay
    severance_loc = input_df.index[input_df['ministry'] == 'Severance Pay'].tolist()
    if severance_loc:
        input_df.loc[severance_loc[0], 'source'] = 'Severance Pay'
        input_df.loc[severance_loc[0], 'ministry'] = 'Pastoral Ministry'

    # print(input_df)
    return input_df


# @st.cache
def get_UN_data():
    data_2018 = clean_summary_data('./data/2018-summary.csv', '2018')
    data_2019 = clean_summary_data('./data/2019-summary.csv', '2019')
    data_2020 = clean_summary_data('./data/2020-summary.csv', '2020')
    # data_2018.join(data_2019, lsuffix='2018')
    # data_2018.join(data_2019, lsuffix='2018')
    data = pd.merge(data_2018, data_2019, how='outer')
    data = pd.merge(data, data_2020, how='outer')

    pastoral_ministry = data[data['ministry'] == 'Pastoral Ministry'].groupby('ministry').agg('sum')
    
    admin = data[data['ministry'] == 'Administrative Support']
    admin = admin[admin['source'].isin([
        'Church Secretary Salary',
        'FICA Tax',
        'Church Secretary Retirement',
        'Medical Insurance'
        ])].groupby('ministry').agg('sum')

    custodian = data[data['ministry'] == 'Facility Support']
    custodian = custodian[custodian['source'].isin([
        'Custodian Salary',
        'FICA Tax',
        'Medical Insurance',
        'Custodian Retirement'
    ])].groupby('ministry').agg('sum')

    data = pd.concat([pastoral_ministry, admin, custodian])
    return data.rename(index={
        "Pastoral Ministry": "Pastor",
        "Administrative Support": "Office Manager",
        "Facility Support": "Custodian"
        })

def get_pe_data(yearly_growth, repoen_growth, salary_df):
    data_2018 = clean_summary_data('./data/2018-summary.csv', '2018')
    data_2019 = clean_summary_data('./data/2019-summary.csv', '2019')
    data_2020 = clean_summary_data('./data/2020-summary.csv', '2020')
    # data_2018.join(data_2019, lsuffix='2018')
    # data_2018.join(data_2019, lsuffix='2018')
    data = pd.merge(data_2018, data_2019, how='outer')
    data = pd.merge(data, data_2020, how='outer')

    income_2019 = data_2019[data_2019['source'] == 'Tithes and Offerings']['2019'].values[0]
    income_2021 = income_2019 * (1 + repoen_growth)
    income_2022 = income_2021 * (1 + yearly_growth)
    income_2023 = income_2022 * (1 + yearly_growth)
    income_2024 = income_2023 * (1 + yearly_growth)

    p_v_e = pd.concat([
        data[data['type'] == 'Income'].groupby('type').agg('sum'),
        data[data['type'] == 'Expense'].groupby('type').agg('sum')
        ])

    p_v_e['avg'] = p_v_e[['2018', '2019']].mean(axis=1)
    average_expense = p_v_e['avg']['Expense']
    p_v_e = p_v_e.drop(columns=['avg'])

    # remove exitsing salary data
    salary_df.loc['total'] = salary_df.sum(axis=0)
    salary_df['avg'] = salary_df[['2018', '2019']].mean(axis=1)
    salary_avg = salary_df['avg']['total']
    average_expense_less_salary = average_expense - salary_avg
    future_expense = average_expense_less_salary + salary_df['Future']['total']

    # Add new data
    p_v_e['2021'] = [income_2021, future_expense]
    p_v_e['2022'] = [income_2022, future_expense]
    p_v_e['2023'] = [income_2023, future_expense]
    p_v_e['2024'] = [income_2024, future_expense]

    p_v_e.loc['Diff'] = p_v_e.loc['Income'] - p_v_e.loc['Expense']

    

    # print(data[data['type'] == 'Income'].groupby('type').agg('sum'))
    # print(data[data['type'] == 'Expense'].groupby('type').agg('sum'))
    print(p_v_e)
    # print(salary_df)
    # put above into DF
    # get the difference
    # get new data from Judy
    # get average offset from historical data
    # project growth
    # see how long it would take to get back to normal
    # add "recovery" slider for 2021 / repoen


try:
    df = get_UN_data()

    # Inputs
    st.sidebar.header("Pastor")
    pastor = st.sidebar.slider("Total Comp", 50000, 150000, 78000, 1)

    st.sidebar.header("Office Manager")
    om_wage = st.sidebar.slider("Hourly Wage", 8, 30, 20, 1)
    om_hpw = st.sidebar.slider("Hours Per Week", 5, 40, 20, 1)
    om_wpy = st.sidebar.slider("Unpaid Vacation", 0, 5, 2, 1)

    st.sidebar.header("Cleaning Service")
    cs_monthly = st.sidebar.slider("Monthly Cost", 100, 2000, 1000, 1)

    st.sidebar.header("Growth")
    yearly_growth = st.sidebar.slider("Yearly Income Growth%", 0, 100, 5, 1) / 100
    repoen_growth = st.sidebar.slider("Re-open Growth%", 0, 100, 5, 1) / 100

    # Update data
    future = [float(pastor), float(om_hpw * om_wage * (52-om_wpy))*1.0765, float(cs_monthly * 12)]
    df['Future'] = future

    # diff
    diff = df.copy()
    diff['Future Vs 2018'] = diff['Future'] - diff['2018']
    diff['Future Vs 2019'] = diff['Future'] - diff['2019']
    diff['Future Vs 2020'] = diff['Future'] - diff['2020']
    # diff = diff.append(diff.sum(numeric_only=True) name="total")
    diff.loc['Total']= diff.sum()
    diff = diff.drop(columns=['2018','2019', '2020'])

    # Income vs expense
    get_pe_data(yearly_growth, repoen_growth, df.copy())
    
    # Output
    data = df.loc[list(df.index)] 
    st.write("### Personnel Expense", data.style.format("${0:.2f}"))

    data = data.T.reset_index()
    data = pd.melt(data, id_vars=["index"]).rename(
        columns={"index": "year", "value": "Dollars"}
    )
    chart = (
        alt.Chart(data)
        .mark_bar(opacity=0.3)
        .encode(
            x="year:O",
            y=alt.Y("Dollars:Q", stack=True),
            color="ministry:N",
        )
    )
    st.altair_chart(chart, use_container_width=True)
    st.write("### Difference", diff.style.format("${0:.2f}"))
except Exception as e:
    st.error(
        """
        Connection error: %s
    """
        % e
    )