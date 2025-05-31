from django.shortcuts import render, redirect
from django.core.mail import EmailMessage
from .forms import HeartForm
import joblib
import numpy as np
from io import BytesIO
from datetime import datetime
from reportlab.platypus import PageBreak
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.styles import ParagraphStyle

# PDF/reportlab imports
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
)
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.lib.utils import ImageReader


# plotting
import matplotlib.pyplot as plt
import shap

# load your trained model
model = joblib.load('random_forest_heart_disease_model.pkl')
def add_watermark(c: pdfcanvas.Canvas, doc):
    c.saveState()
    wmark = ImageReader('predictor\\static\\images\\heart_logo.jpg')
    iw, ih = wmark.getSize()
    target_width  = doc.pagesize[0] * 0.6
    target_height = (ih/iw) * target_width
    x = (doc.pagesize[0] - target_width) / 2
    y = (doc.pagesize[1] - target_height) / 2

    try:
        c.setFillAlpha(0.1)
    except AttributeError:
        pass

    c.drawImage(wmark, x, y, width=target_width, height=target_height, mask='auto')
    c.restoreState()


def predict(request):
    result = None
    confidence = None

    if request.method == 'POST':
        form = HeartForm(request.POST)
        if form.is_valid():
            # 1) Prepare input array
            feature_names = [f for f in form.fields if f != 'name']
            feature_labels = [form[field].label for field in feature_names]
            data = np.array([[form.cleaned_data[f] for f in feature_names]])
            data = data.astype(np.float64)

            # 2) Model prediction & confidence
            prediction = model.predict(data)[0]
            probas = model.predict_proba(data)[0]
            confidence_score = probas[prediction] * 100
            result = (
                "You may have Heart Disease"
                if prediction == 1 else
                "You are likely healthy"
            )
            confidence = f"{confidence_score:.2f}% confidence"
            user_name = form.cleaned_data.get('name', 'User')

            # 3) If user requested report, build PDF
            if 'send_report' in request.POST:
                email = request.POST.get('email')
                if email:
                    buffer = BytesIO()
                    pdf = SimpleDocTemplate(buffer, pagesize=letter)
                    elements = []

                    # Styles
                    styles = getSampleStyleSheet()
                    title_style = styles['Heading1']
                    title_style.textColor = colors.HexColor('#004d99')
                    title_style.alignment = TA_CENTER 
                    subtitle_style = styles['Heading3']
                    subtitle_style.textColor = colors.HexColor('#003366')

                    timestamp_style = ParagraphStyle(
                        name='Timestamp',
                        parent=styles['Normal'],     
                        alignment=TA_RIGHT,          
                        textColor=colors.HexColor('#003366'),
                        spaceAfter=12                 
                    )
                    def get_ordinal(n):
                        return f"{n}{'th' if 11 <= n%100 <= 13 else {1:'st',2:'nd',3:'rd'}.get(n%10,'th')}"
                    now_dt = datetime.now()
                    hour = now_dt.strftime('%I').lstrip('0') or '0'
                    formatted_date = (
                        f"{get_ordinal(now_dt.day)} {now_dt.strftime('%B %Y')}, "
                        f"{hour}:{now_dt.strftime('%M %p')}"
                    )
                    elements.append(Paragraph(f"Date & Time: {formatted_date}", timestamp_style))
                    # Title & user info
                    elements.append(Paragraph("Heart Disease Prediction Report", title_style))
                    elements.append(Spacer(1, 12))


                    elements.append(Paragraph(f"Name of patient: {user_name}", subtitle_style))
                    elements.append(Paragraph(f"<b>Result:</b> {result}", styles['Normal']))
                    elements.append(Paragraph(f"<b>Confidence:</b> {confidence}", styles['Normal']))
                    elements.append(Spacer(1, 12))

                    # Field mappings for readability
                    field_mappings = {
                        'sex': {'0': 'Female', '1': 'Male'},
                        'fbs': {'0': 'No', '1': 'Yes'},
                        'exang': {'0': 'No', '1': 'Yes'},
                        'cp': {
                            '1': 'Typical Angina',
                            '2': 'Atypical Angina',
                            '3': 'Non-anginal Pain',
                            '4': 'Asymptomatic'
                        },
                        'restecg': {
                            '0': 'Normal',
                            '1': 'ST-T Wave Abnormality',
                            '2': 'Left Ventricular Hypertrophy'
                        },
                        'num': {
                            '1': 'Up Sloping',
                            '2': 'Flat',
                            '3': 'Down Sloping'
                        }
                    }
                    input_data = [["Field", "Value"]]
                    for field in form.fields:
                        label = form[field].label
                        val = form.cleaned_data[field]
                        if field in field_mappings:
                            val = field_mappings[field].get(val, val)
                        input_data.append([label, str(val)])
                    tbl = Table(input_data, colWidths=[2.5*inch, 3.5*inch])
                    tbl.setStyle(TableStyle([
                        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#cce5ff")),
                        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor("#003366")),
                        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                        ('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
                        ('BOX', (0,0), (-1,-1), 0.5, colors.black),
                    ]))
                    elements += [tbl, Spacer(1, 24)]

                    # --- Instance-level SHAP explanation ---
                    explainer   = shap.TreeExplainer(model)
                    shap_vals   = explainer.shap_values(data) 
                    neg_shap    = shap_vals[0, :, 0]
                    pos_shap    = shap_vals[0, :, 1]

                    # choose values for the predicted class
                    if prediction == 1:
                        vals = pos_shap; title_extra = " (risk factors)"
                    else:
                        vals = neg_shap; title_extra = " (protective factors)"

                    # prepare pie data
                    abs_vals = np.abs(vals)
                    total    = abs_vals.sum() or 1
                    percents = (abs_vals / total) * 100

                    # pick distinct colors
                    cmap   = plt.get_cmap('tab20')
                    colors_ = cmap(np.linspace(0, 1, len(feature_names)))
                    legend_labels = [
                        f"{label} ({p:.1f}%)"
                        for label, p in zip(feature_labels, percents)
                    ]
                    # draw pie
                    fig, ax = plt.subplots(figsize=(6,6))
                    wedges, texts, autotexts = ax.pie(
                        percents,
                        startangle=90,
                        colors=colors_,
                        labels=None,
                        autopct='%.1f%%',
                        pctdistance=0.85,
                        textprops={'fontsize': 8},
                        wedgeprops={'linewidth':0.5, 'edgecolor':'white'}
                    )
                    ax.legend(
                        wedges,
                        legend_labels,
                        title="Features",
                        loc="center left",
                        bbox_to_anchor=(1, 0, 0.3, 1),
                        fontsize=8,
                        title_fontsize=9
                    )
                    ax.set_title(f"Feature importance breakdown{title_extra}", pad=20)
                    ax.axis('equal')
                    plt.tight_layout()

                    buf_pie = BytesIO()
                    fig.savefig(buf_pie, format='PNG', dpi=150, bbox_inches='tight')
                    plt.close(fig)
                    buf_pie.seek(0)
                    elements.append(PageBreak())
                    elements.append(Paragraph(
                        "Feature Important Analysis:",
                        styles['Heading3']
                    ))
                    elements.append(Spacer(1, 12))
                    elements.append(Image(buf_pie, width=5*inch, height=5*inch))
                    elements.append(Spacer(1, 24))

                    # Disclaimer
                    elements.append(Paragraph(
                        "Disclaimer: This report is generated by an AI-based predictive model using the data you provided. "
                        "It is not a substitute for professional medical advice, diagnosis, or treatment. "
                        "Always seek the guidance of a qualified healthcare provider with any questions you may have regarding your health.",
                        styles['Italic']
                    ))

                    # build PDF
                    pdf.build(
                        elements,
                        onFirstPage=add_watermark,
                        onLaterPages=add_watermark
                    )
                    buffer.seek(0)

                    # send email
                    subject = "Heart Disease Prediction Report"
                    body = (
                        f"Hello {user_name},\n\n"
                        f"Attached is your heart disease prediction report generated on {formatted_date}.\n"
                        "Please consult your doctor for further advice.\n\n"
                        "Regards,\nHeart Prediction Team"
                    )
                    email_msg = EmailMessage(subject, body,
                                             from_email='manikantamitproject@example.com',
                                             to=[email])
                    email_msg.attach(f"{user_name}_Heart_Report.pdf",
                                     buffer.read(), 'application/pdf')
                    email_msg.send()

                    request.session['result'] = result + " (PDF report sent to your email!)"
                else:
                    request.session['result'] = result
            else:
                request.session['result'] = result

            request.session['confidence'] = confidence
            return redirect('predict')

    else:
        form = HeartForm()
        result = request.session.pop('result', None)
        confidence = request.session.pop('confidence', None)

    return render(request, 'predictor/form.html', {
        'form': form,
        'result': result,
        'confidence': confidence
    })
