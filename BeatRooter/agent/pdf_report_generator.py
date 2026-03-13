import json
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

class PDFReportGenerator:
    def __init__(self, json_report_path="detailed_security_report.json"):
        self.json_report_path = json_report_path
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
    
    def setup_custom_styles(self):
        self.styles.add(ParagraphStyle(
            name='MainTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            textColor=colors.darkred,
            spaceAfter=30,
            alignment=1
        ))
        
        self.styles.add(ParagraphStyle(
            name='SubTitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.darkblue,
            spaceAfter=12,
            spaceBefore=12
        ))
        
        self.styles.add(ParagraphStyle(
            name='CriticalVuln',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.red,
            backColor=colors.mistyrose,
            borderPadding=5,
            spaceAfter=6
        ))
        
        self.styles.add(ParagraphStyle(
            name='HighVuln',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.darkorange,
            backColor=colors.lemonchiffon,
            borderPadding=5,
            spaceAfter=6
        ))

    def generate_pdf_report(self, output_path="security_report.pdf"):
        try:
            with open(self.json_report_path, 'r', encoding='utf-8') as f:
                report_data = json.load(f)

            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=18
            )
            
            story = []
            
            # Header
            story.extend(self._create_header(report_data))
            
            # Summary
            story.extend(self._create_executive_summary(report_data))
            
            # Análise de Risco
            story.extend(self._create_risk_analysis(report_data))
            
            # Vulnerabilidades Detalhadas
            story.extend(self._create_vulnerabilities_section(report_data))
            
            # Plano de Ação
            story.extend(self._create_action_plan(report_data))
            
            # Recomendações Técnicas
            story.extend(self._create_technical_recommendations(report_data))
            
            # Footer
            story.extend(self._create_footer())

            doc.build(story)
            return True
            
        except Exception as e:
            print(f"Erro ao gerar PDF: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return False

    def _create_header(self, report_data):
        elements = []
        
        # Título
        title = Paragraph("RELATÓRIO DE SEGURANÇA - ANÁLISE DE VULNERABILIDADES", self.styles['MainTitle'])
        elements.append(title)
        elements.append(Spacer(1, 20))
        
        # Metadados
        metadata = report_data['metadata']
        exec_summary = report_data['executive_summary']
        
        info_table_data = [
            ["Alvo Analisado:", metadata['target_url']],
            ["Data da Análise:", metadata['scan_date']],
            ["Total de Vulnerabilidades:", str(exec_summary['total_vulnerabilities'])],
            ["Risco Global:", f"{exec_summary['overall_risk']}"],
            ["Versão do Scanner:", metadata['scanner_version']]
        ]
        
        info_table = Table(info_table_data, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ]))
        
        elements.append(info_table)
        elements.append(Spacer(1, 20))
        
        return elements

    def _create_executive_summary(self, report_data):
        elements = []
        
        elements.append(Paragraph("SUMÁRIO EXECUTIVO", self.styles['SubTitle']))
        
        exec_summary = report_data['executive_summary']
        risk_assessment = report_data['risk_assessment']
        
        summary_text = f"""
        Esta análise de segurança identificou <b>{exec_summary['total_vulnerabilities']}</b> vulnerabilidades no sistema analisado, 
        sendo <b>{exec_summary['critical_vulnerabilities']}</b> classificadas como críticas e 
        <b>{exec_summary['high_vulnerabilities']}</b> como alta severidade.
        
        O nível de risco geral foi classificado como <b>{exec_summary['overall_risk']}</b> com um score de risco de 
        <b>{risk_assessment['overall_risk_score']}</b>.
        """
        
        elements.append(Paragraph(summary_text, self.styles['Normal']))
        elements.append(Spacer(1, 12))
        
        elements.append(Paragraph("PRINCIPAIS ACHADOS:", self.styles['Heading3']))
        for finding in exec_summary['key_findings']:
            elements.append(Paragraph(f"• {finding}", self.styles['Normal']))
        
        elements.append(Spacer(1, 20))
        return elements

    def _create_risk_analysis(self, report_data):
        elements = []
        
        elements.append(Paragraph("ANÁLISE DE RISCO", self.styles['SubTitle']))
        
        risk_data = report_data['risk_assessment']
        
        risk_table_data = [
            ["Categoria", "Quantidade", "Score"],
            ["Críticas", str(risk_data['critical_vulnerabilities']), "10 pts cada"],
            ["Altas", str(risk_data['high_vulnerabilities']), "7 pts cada"],
            ["Médias", str(risk_data['medium_vulnerabilities']), "4 pts cada"],
            ["", "SCORE TOTAL:", f"{risk_data['overall_risk_score']}"],
            ["", "NÍVEL DE RISCO:", f"{risk_data['risk_level']}"]
        ]
        
        risk_table = Table(risk_table_data, colWidths=[2*inch, 1.5*inch, 2*inch])
        risk_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 1), (-1, -2), colors.lightgrey),
            ('BACKGROUND', (0, -2), (-1, -1), colors.lightsteelblue),
            ('TEXTCOLOR', (0, -2), (-1, -1), colors.darkred),
        ]))
        
        elements.append(risk_table)
        elements.append(Spacer(1, 20))
        return elements

    def _create_vulnerabilities_section(self, report_data):
        elements = []
        
        elements.append(Paragraph("VULNERABILIDADES DETALHADAS", self.styles['SubTitle']))
        
        vulnerabilities = report_data['vulnerabilities']
        
        for i, vuln in enumerate(vulnerabilities, 1):
            if vuln['severity'] == "Crítica":
                style = self.styles['CriticalVuln']
                severity_icon = "🔴"
            elif vuln['severity'] == "Alta":
                style = self.styles['HighVuln']
                severity_icon = "🟠"
            else:
                style = self.styles['Normal']
                severity_icon = "🟡"
            
            cvss_score = vuln.get('cvss_score', 0.0)
            business_impact = vuln.get('business_impact', 'Não especificado')
            payload = vuln.get('payload', '')
            exploited = vuln.get('exploited', False)
            
            vuln_text = f"""
            <b>{severity_icon} {vuln['type']} - {vuln['severity']} (CVSS: {cvss_score})</b><br/>
            <b>Localização:</b> {vuln['location']}<br/>
            <b>Descrição:</b> {vuln['description']}<br/>
            <b>Impacto:</b> {business_impact}<br/>
            <b>Status:</b> {'EXPLORADA' if exploited else 'DETECTADA'}<br/>
            """
            
            if payload:
                vuln_text += f"<b>Payload:</b> <font face='Courier'>{payload}</font><br/>"
            
            elements.append(Paragraph(vuln_text, style))
            elements.append(Spacer(1, 10))
        
        return elements

    def _create_action_plan(self, report_data):
        elements = []
        
        elements.append(Paragraph("PLANO DE AÇÃO IMEDIATO", self.styles['SubTitle']))
        
        action_plan = report_data['remediation_plan']
        
        for i, action in enumerate(action_plan['immediate_actions'], 1):
            action_text = f"""
            <b>{i}. {action['vulnerability']}</b><br/>
            <b>Ação:</b> {action['action']}<br/>
            <b>Esforço Estimado:</b> {action['estimated_effort']}<br/>
            <b>Prioridade:</b> {action['priority']}<br/>
            <b>Ficheiros Afetados:</b> {', '.join(action['files_affected'])}<br/>
            """
            
            elements.append(Paragraph(action_text, self.styles['Normal']))
            elements.append(Spacer(1, 8))
        
        elements.append(Spacer(1, 20))
        return elements

    def _create_technical_recommendations(self, report_data):
        elements = []
        
        elements.append(Paragraph("RECOMENDAÇÕES TÉCNICAS", self.styles['SubTitle']))
        
        recommendations = report_data['security_recommendations']
        
        elements.append(Paragraph("Ações Críticas:", self.styles['Heading3']))
        for rec in recommendations['critical_recommendations']:
            elements.append(Paragraph(f"<b>{rec['title']}</b>", self.styles['Normal']))
            for step in rec['steps']:
                elements.append(Paragraph(f"• {step}", self.styles['Normal']))
            elements.append(Spacer(1, 8))
        
        elements.append(Spacer(1, 12))
        return elements

    def _create_footer(self):
        elements = []
        
        elements.append(Spacer(1, 20))
        footer_text = f"""
        <i>Relatório gerado automaticamente por Nábia Security Agent<br/>
        Data de geração: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>
        Este é um relatório confidencial para uso interno.</i>
        """
        
        elements.append(Paragraph(footer_text, self.styles['Italic']))
        return elements