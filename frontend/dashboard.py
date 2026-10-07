"""
Public Pulse dashboard UI.

Shows aggregated civic complaint statistics.
"""

import altair as alt
import pandas as pd
import streamlit as st

from frontend.api_client import (
    APIClientError,
    get_city_comparison,
    get_dashboard_cities,
    get_dashboard_summary,
)


PERIOD_OPTIONS = {
    "All time": None,
    "Last 7 days": 7,
    "Last 30 days": 30,
    "Last 90 days": 90,
    "Custom": "custom",
}


def _dict_to_dataframe(
        data: dict[str, int],
        *,
        label_column: str,
) -> pd.DataFrame:
    """
    Convert dashboard dictionaries into a DataFrame suitable
    for Streamlit charts.

    Example:

    {
        "road": 5,
        "water": 3
    }

    becomes:

    category | complaints
    ---------------------
    road     | 5
    water    | 3
    """

    return pd.DataFrame(
        [
            {
                label_column: key,
                "complaints": value,
            }
            for key, value in data.items()
        ]
    )


def _format_city_option(
        city: dict,
) -> str:
    """
    Display a city option with enough context for comparison.
    """

    population = city.get(
        "population",
    )

    if population:
        return (
            f"{city['name']} "
            f"(population {population:,})"
        )

    return city["name"]


def show_dashboard() -> None:
    """
    Display the Public Pulse civic complaint dashboard.
    """

    st.header(
        "Civic Dashboard"
    )

    selected_period = st.selectbox(
        "Time period",
        options=list(
            PERIOD_OPTIONS.keys()
        ),
    )

    selected_value = PERIOD_OPTIONS[selected_period]

    if selected_value == "custom":
        days = st.number_input(
            "Number of days",
            min_value=1,
            max_value=365,
            value=30,
            step=1,
        )
    else:
        days = selected_value

    try:
        summary = get_dashboard_summary(
            days=days,
        )

    except APIClientError as exc:
        st.error(
            str(exc),
        )
        return

    # -----------------------------------------------------
    # Main metric
    # -----------------------------------------------------

    st.metric(
        label="Total complaints",
        value=summary["total_complaints"],
    )

    st.caption(
        (
            "All complaints"
            if days is None
            else (
                f"Complaints created in the "
                f"last {days} days"
            )
        )
    )

    # -----------------------------------------------------
    # City comparison
    # -----------------------------------------------------

    st.subheader(
        "Compare cities per 10,000 people"
    )

    try:
        cities = get_dashboard_cities()

    except APIClientError as exc:
        st.error(
            str(exc),
        )
        cities = []

    comparable_cities = [
        city
        for city in cities
        if city.get("population")
    ]

    if len(comparable_cities) >= 2:
        first_city, second_city = st.columns(2)

        with first_city:
            selected_first_city = st.selectbox(
                "First city",
                options=comparable_cities,
                format_func=_format_city_option,
                key="first_comparison_city",
            )

        second_city_options = [
            city
            for city in comparable_cities
            if city["id"] != selected_first_city["id"]
        ]

        with second_city:
            selected_second_city = st.selectbox(
                "Second city",
                options=second_city_options,
                format_func=_format_city_option,
                key="second_comparison_city",
            )

        try:
            comparison = get_city_comparison(
                city_ids=[
                    selected_first_city["id"],
                    selected_second_city["id"],
                ],
                days=days,
            )

        except APIClientError as exc:
            st.error(
                str(exc),
            )

        else:
            comparison_df = pd.DataFrame(
                comparison["category_rates"]
            )

            comparison_df = comparison_df.rename(
                columns={
                    "city_name": "city",
                    "complaint_count": "complaints",
                    "complaints_per_10000": "complaints_per_10000",
                }
            )

            comparison_df["display_category"] = (
                comparison_df["category"]
                .str.replace(
                    "_",
                    " ",
                )
                .str.title()
            )

            category_order = list(
                comparison_df[
                    "display_category"
                ].drop_duplicates()
            )

            city_order = [
                selected_first_city["name"],
                selected_second_city["name"],
            ]

            comparison_chart = (
                alt.Chart(
                    comparison_df,
                    title=(
                        f"{selected_first_city['name']} and "
                        f"{selected_second_city['name']}"
                    ),
                )
                .mark_bar()
                .encode(
                    x=alt.X(
                        "display_category:N",
                        title="Complaint Category",
                        sort=category_order,
                        axis=alt.Axis(
                            labelAngle=0,
                        ),
                    ),
                    xOffset=alt.XOffset(
                        "city:N",
                        sort=city_order,
                    ),
                    y=alt.Y(
                        "complaints_per_10000:Q",
                        title="Complaints per 10,000 people",
                        axis=alt.Axis(
                            grid=True,
                        ),
                    ),
                    color=alt.Color(
                        "city:N",
                        title=None,
                        scale=alt.Scale(
                            domain=city_order,
                            range=[
                                "#4285F4",
                                "#EA4335",
                            ],
                        ),
                        legend=alt.Legend(
                            orient="top",
                            direction="horizontal",
                            symbolType="square",
                        ),
                    ),
                    tooltip=[
                        alt.Tooltip(
                            "city:N",
                            title="City",
                        ),
                        alt.Tooltip(
                            "display_category:N",
                            title="Category",
                        ),
                        alt.Tooltip(
                            "population:Q",
                            title="Population",
                            format=",",
                        ),
                        alt.Tooltip(
                            "complaints:Q",
                            title="Complaints",
                        ),
                        alt.Tooltip(
                            "complaints_per_10000:Q",
                            title="Per 10,000 people",
                        ),
                    ],
                )
                .properties(
                    width=760,
                    height=420,
                )
                .configure_title(
                    anchor="start",
                    fontSize=28,
                    color="#6f6f6f",
                    fontWeight="normal",
                    offset=18,
                )
                .configure_axis(
                    labelFontSize=14,
                    titleFontSize=14,
                    gridColor="#dddddd",
                    domainColor="#555555",
                    tickColor="#555555",
                )
                .configure_legend(
                    labelFontSize=14,
                    orient="top",
                )
            )

            st.altair_chart(
                comparison_chart,
                use_container_width=True,
            )

    else:
        st.info(
            "Add population data for at least two cities to compare rates."
        )

    # -----------------------------------------------------
    # Status
    # -----------------------------------------------------

    st.subheader(
        "Complaints by status"
    )

    status_data = summary[
        "by_status"
    ]

    if status_data:
        status_df = _dict_to_dataframe(
            status_data,
            label_column="status",
        )

        st.bar_chart(
            status_df,
            x="status",
            y="complaints",
            sort="-complaints",
        )

    else:
        st.info(
            "No status data for this period."
        )

    # -----------------------------------------------------
    # Category
    # -----------------------------------------------------

    st.subheader(
        "Complaints by category"
    )

    category_data = summary[
        "by_category"
    ]

    if category_data:
        category_df = _dict_to_dataframe(
            category_data,
            label_column="category",
        )
        category_df = category_df.sort_values(
            by="complaints",
            ascending=False,
        )

        st.bar_chart(
            category_df,
            x="category",
            y="complaints",
            sort="-complaints",
        )

        # st.dataframe(
        #     category_df,
        #     use_container_width=True,
        #     hide_index=True,
        # )

    else:
        st.info(
            "No category data for this period."
        )

    # -----------------------------------------------------
    # Pincode
    # -----------------------------------------------------

    st.subheader(
        "Complaints by pincode"
    )

    pincode_data = summary[
        "by_pincode"
    ]

    if pincode_data:
        pincode_df = _dict_to_dataframe(
            pincode_data,
            label_column="pincode",
        )
        pincode_df = pincode_df.sort_values(
                by="complaints",
                ascending=False,
            )

        st.bar_chart(
            pincode_df,
            x="pincode",
            y="complaints",
            sort="-complaints",
        )

    else:
        st.info(
            "No pincode data for this period."
        )
