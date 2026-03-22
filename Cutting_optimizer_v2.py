## Cutting Optimizer v2.0

import streamlit as st
import matplotlib.pyplot as plt
from io import BytesIO

# PDF
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet


# ---------------- OPTIMIZATION ----------------
def calculate_cutting_plan(standard_length, kerf, cuts_required):

    all_pieces = []
    for item in cuts_required:
        all_pieces.extend([item['length']] * item['qty'])

    all_pieces.sort(reverse=True)
    bars = []

    for piece in all_pieces:
        best_bar_index = -1
        min_remaining_space = standard_length + 1

        for i, bar in enumerate(bars):
            current_used = sum(bar) + (max(0, len(bar)-1) * kerf)
            space_left = standard_length - current_used

            needed_space = piece if len(bar) == 0 else piece + kerf

            if needed_space <= space_left:
                if space_left - needed_space < min_remaining_space:
                    min_remaining_space = space_left - needed_space
                    best_bar_index = i

        if best_bar_index != -1:
            bars[best_bar_index].append(piece)
        else:
            bars.append([piece])

    total_waste = 0

    for bar in bars:
        used = sum(bar)
        waste = standard_length - (used + (max(0, len(bar)-1) * kerf))
        total_waste += waste

    efficiency = ((len(bars)*standard_length - total_waste) / (len(bars)*standard_length)) * 100

    return bars, len(bars), total_waste, round(efficiency, 2)


# ---------------- GROUPING ----------------
def group_bars(bars):
    grouped = {}
    for bar in bars:
        pattern = tuple(sorted(bar, reverse=True))
        grouped[pattern] = grouped.get(pattern, 0) + 1
    return grouped


# ---------------- GRAPH ----------------
def draw_grouped_bars(grouped_bars, standard_length):
    fig, ax = plt.subplots(figsize=(10, 4))

    for i, (pattern, count) in enumerate(grouped_bars.items()):
        left = 0

        for cut in pattern:
            ax.barh(i, cut, left=left, edgecolor='black')

            if cut > 120:
                ax.text(left + cut/2, i, str(cut),
                        ha='center', va='center', fontsize=8)

            left += cut

        waste = standard_length - left
        if waste > 0:
            ax.barh(i, waste, left=left, edgecolor='black')

        ax.text(standard_length + 50, i, f"{count} Bars",
                va='center', fontsize=9, fontweight='bold')

    ax.set_xlim(0, standard_length + 300)
    ax.set_xlabel("Length (mm)")
    ax.set_yticks(range(len(grouped_bars)))
    ax.set_yticklabels([f"Pattern {i+1}" for i in range(len(grouped_bars))])
    ax.set_title("Grouped Cutting Layout")

    ax.invert_yaxis()
    plt.tight_layout()

    return fig


# ---------------- PDF ----------------
def generate_pdf_bytes(standard_length, kerf, total_bars, waste, efficiency, grouped, fig, cuts_required):

    buffer = BytesIO()

    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()

    content = []

    content.append(Paragraph("<b>Cutting Optimization Report</b>", styles["Title"]))
    content.append(Spacer(1, 10))

    content.append(Paragraph(f"Standard Length: {standard_length} mm", styles["Normal"]))
    content.append(Paragraph(f"Kerf: {kerf} mm", styles["Normal"]))
    content.append(Spacer(1, 10))

    content.append(Paragraph(f"Total Bars Needed: {total_bars}", styles["Normal"]))
    content.append(Paragraph(f"Total Waste: {waste} mm", styles["Normal"]))
    content.append(Paragraph(f"Efficiency: {efficiency} %", styles["Normal"]))
    content.append(Spacer(1, 15))

    # ✅ NEW: Input Table
    content.append(Paragraph("<b>Input Cut Details:</b>", styles["Heading2"]))
    content.append(Spacer(1, 10))

    input_data = [["Length (mm)", "Quantity"]]
    for item in cuts_required:
        input_data.append([item["length"], item["qty"]])

    content.append(Table(input_data))
    content.append(Spacer(1, 15))

    # Pattern Table
    content.append(Paragraph("<b>Pattern Summary:</b>", styles["Heading2"]))
    content.append(Spacer(1, 10))

    data = [["Pattern", "Count"]]
    for pattern, count in grouped.items():
        data.append([str(pattern), count])

    content.append(Table(data))
    content.append(Spacer(1, 20))

    # Plot Image
    img_buffer = BytesIO()
    fig.savefig(img_buffer, format="png", bbox_inches='tight')
    img_buffer.seek(0)

    content.append(Image(img_buffer, width=500, height=250))

    doc.build(content)

    buffer.seek(0)
    return buffer


# ---------------- UI ----------------
st.set_page_config(page_title="Cutting Optimizer", layout="centered")

st.title("🔧 Cutting Optimization Tool")

standard_length = st.number_input("Standard Length (mm)", value=3000)
kerf = st.number_input("Kerf (mm)", value=10)

st.subheader("Cut Details")

cuts = []
rows = st.number_input("Number of cut types", 1, 10, 3)

for i in range(rows):
    col1, col2 = st.columns(2)
    l = col1.number_input(f"Length {i+1}", key=f"l{i}")
    q = col2.number_input(f"Qty {i+1}", key=f"q{i}")

    if l > 0 and q > 0:
        cuts.append({"length": int(l), "qty": int(q)})


# ---------------- ACTION ----------------
if st.button("Calculate"):

    bars, total_bars, waste, efficiency = calculate_cutting_plan(
        int(standard_length), int(kerf), cuts
    )

    grouped = group_bars(bars)

    st.subheader("📊 Results")
    st.write("Total Bars Needed:", total_bars)
    st.write("Total Waste:", waste, "mm")
    st.write("Efficiency:", efficiency, "%")

    st.subheader("📦 Pattern Summary")
    for pattern, count in grouped.items():
        st.write(f"{count} Bars → {list(pattern)}")

    st.subheader("📊 Layout")
    fig = draw_grouped_bars(grouped, standard_length)
    st.pyplot(fig)

    # ✅ PDF Download
    pdf_buffer = generate_pdf_bytes(
        standard_length,
        kerf,
        total_bars,
        waste,
        efficiency,
        grouped,
        fig,
        cuts
    )

    st.download_button(
        label="📄 Download PDF",
        data=pdf_buffer,
        file_name="cutting_report.pdf",
        mime="application/pdf"
    )

    ## Done..##