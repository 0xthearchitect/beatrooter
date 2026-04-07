import json
from datetime import datetime

class MarkdownReportGenerator:
    def __init__(self, json_report_path="detailed_security_report.json"):
        self.json_report_path = json_report_path
    
    def generate_markdown_report(self, output_path="security_report.md"):
        try:
            with open(self.json_report_path, 'r', encoding='utf-8') as f:
                report_data = json.load(f)
            
            markdown_content = self._build_markdown_content(report_data)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            return True
            
        except Exception as e:
            print(f"Erro ao gerar Markdown: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return False
    
    def _build_markdown_content(self, report_data):
        content = []
        
        # Header
        content.extend(self._create_markdown_header(report_data))
        
        # Summary
        content.extend(self._create_markdown_executive_summary(report_data))
        
        # Análise de Risco
        content.extend(self._create_markdown_risk_analysis(report_data))
        
        # Vulnerabilidades Detalhadas
        content.extend(self._create_markdown_vulnerabilities(report_data))
        
        # Plano de Ação
        content.extend(self._create_markdown_action_plan(report_data))
        
        # Recomendações Técnicas
        content.extend(self._create_markdown_recommendations(report_data))
        
        # Footer
        content.extend(self._create_markdown_footer())
        
        return '\n'.join(content)
    
    def _create_markdown_header(self, report_data):
        metadata = report_data['metadata']
        
        return [
            "# RELATÓRIO DE SEGURANÇA - ANÁLISE DE VULNERABILIDADES",
            "",
            "---",
            "",
            "## Informações da Análise",
            "",
            f"**Alvo Analisado:** {metadata['target_url']}",
            f"**Data da Análise:** {metadata['scan_date']}",
            f"**Versão do Scanner:** {metadata['scanner_version']}",
            "",
            "---",
            ""
        ]
    
    def _create_markdown_executive_summary(self, report_data):
        exec_summary = report_data['executive_summary']
        risk_assessment = report_data['risk_assessment']
        
        medium_low_count = exec_summary['total_vulnerabilities'] - exec_summary['critical_vulnerabilities'] - exec_summary['high_vulnerabilities']
        
        return [
            "## Sumário Executivo",
            "",
            f"Esta análise de segurança identificou **{exec_summary['total_vulnerabilities']} vulnerabilidades** no sistema analisado:",
            "",
            f"- 🔴 **{exec_summary['critical_vulnerabilities']} Críticas**",
            f"- 🟠 **{exec_summary['high_vulnerabilities']} Altas**",
            f"- 🟡 **{medium_low_count} Médias/Baixas**",
            "",
            f"**Nível de Risco Global:** `{exec_summary['overall_risk']}`",
            f"**Score de Risco:** `{risk_assessment['overall_risk_score']}/40`",
            "",
            "### Principais Achados",
            ""
        ] + [f"- {finding}" for finding in exec_summary['key_findings']] + ["", "---", ""]
    
    def _create_markdown_risk_analysis(self, report_data):
        risk_data = report_data['risk_assessment']
        
        return [
            "## Análise de Risco",
            "",
            "| Categoria | Quantidade | Pontuação |",
            "|-----------|------------|-----------|",
            f"| Críticas | {risk_data['critical_vulnerabilities']} | 10 pts cada |",
            f"| Altas | {risk_data['high_vulnerabilities']} | 7 pts cada |",
            f"| Médias | {risk_data['medium_vulnerabilities']} | 4 pts cada |",
            f"| **TOTAL** | **{risk_data['critical_vulnerabilities'] + risk_data['high_vulnerabilities'] + risk_data['medium_vulnerabilities']}** | **{risk_data['overall_risk_score']}/40** |",
            "",
            f"**Nível de Risco:** `{risk_data['risk_level']}`",
            "",
            "---",
            ""
        ]
    
    def _create_markdown_vulnerabilities(self, report_data):
        vulnerabilities = report_data['vulnerabilities']
        
        content = [
            "## Vulnerabilidades Detalhadas",
            ""
        ]
        
        for i, vuln in enumerate(vulnerabilities, 1):
            if vuln['severity'] == "Crítica":
                icon = "🔴"
            elif vuln['severity'] == "Alta":
                icon = "🟠"
            else:
                icon = "🟡"
            
            cvss_score = vuln.get('cvss_score', 0.0)
            business_impact = vuln.get('business_impact', 'Não especificado')
            payload = vuln.get('payload', '')
            exploited = vuln.get('exploited', False)
            recommendation = vuln.get('recommendation', 'Revisar e corrigir a vulnerabilidade identificada')
            code_snippet = vuln.get('code_snippet', '')
            fixed_code_example = vuln.get('fixed_code_example', '')
            
            content.extend([
                f"### {icon} Vulnerabilidade {i}: {vuln['type']}",
                "",
                f"**Severidade:** `{vuln['severity']}`",
                f"**CVSS Score:** `{cvss_score}/10`",
                f"**Localização:** {vuln['location']}",
                f"**Status:** `{'EXPLORADA' if exploited else 'DETECTADA'}`",
                "",
                f"**Descrição:** {vuln['description']}",
                "",
                f"**Impacto de Negócio:** {business_impact}",
                ""
            ])
            
            if payload:
                content.extend([
                    f"**Payload Utilizado:**",
                    f"```",
                    f"{payload}",
                    f"```",
                    ""
                ])
            
            if code_snippet:
                content.extend([
                    "**Código Vulnerável:**",
                    "```python",
                    code_snippet,
                    "```",
                    ""
                ])
            
            if fixed_code_example:
                content.extend([
                    "**Código Corrigido:**",
                    "```python",
                    fixed_code_example,
                    "```",
                    ""
                ])
            
            content.extend([
                f"**Recomendação:** {recommendation}",
                "",
                "---",
                ""
            ])
        
        return content
    
    def _create_markdown_action_plan(self, report_data):
        action_plan = report_data['remediation_plan']
        
        content = [
            "## Plano de Ação Imediato",
            "",
            "### Ações Prioritárias (1-4 horas)",
            ""
        ]
        
        for i, action in enumerate(action_plan['immediate_actions'], 1):
            content.extend([
                f"#### {i}. {action['vulnerability']}",
                "",
                f"- **Ação:** {action['action']}",
                f"- **Esforço:** {action['estimated_effort']}",
                f"- **Prioridade:** {action['priority']}",
                f"- **Ficheiros:** {', '.join(action['files_affected'])}",
                ""
            ])
        
        content.extend(["---", ""])
        return content
    
    def _create_markdown_recommendations(self, report_data):
        recommendations = report_data['security_recommendations']
        
        content = [
            "## Recomendações de Segurança",
            "",
            "### Ações Críticas"
        ]
        
        for rec in recommendations['critical_recommendations']:
            content.extend([
                f"#### {rec['title']}",
                ""
            ] + [f"- {step}" for step in rec['steps']] + [""])
        
        content.extend([
            "### Melhorias de Configuração",
            ""
        ] + [f"- {improvement}" for improvement in recommendations.get('configuration_improvements', [])] + [""])
        
        content.extend([
            "### Boas Práticas de Desenvolvimento",
            ""
        ] + [f"- {practice}" for practice in recommendations.get('development_best_practices', [])] + [""])
        
        return content
    
    def _create_markdown_footer(self):
        return [
            "---",
            "",
            f"*Relatório gerado automaticamente por Nábia Security Agent*  ",
            f"*Data de geração: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*  ",
            "*Este é um relatório confidencial para uso interno.*"
        ]