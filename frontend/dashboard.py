"""
Public Pulse dashboard UI.

Shows aggregated civic complaint statistics.
"""

import pandas as pd
import streamlit as st

from frontend.api_client import (
    APIClientError,
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

        st.bar_chart(
            category_df,
            x="category",
            y="complaints",
        )

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

        st.bar_chart(
            pincode_df,
            x="pincode",
            y="complaints",
        )

    else:
        st.info(
            "No pincode data for this period."
        )