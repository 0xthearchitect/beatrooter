import json
import time
from datetime import datetime
from typing import List, Dict, Any
from agent.pentest_agent import SecurityVulnerability

class JSONReportGenerator:
    def __init__(self, vulnerabilities: List[SecurityVulnerability], target_url: str):
        self.vulnerabilities = vulnerabilities
        self.target_url = target_url
    
    def generate_json_report(self, output_path: str) -> bool:
        try:
            report = self._build_report_structure()
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"Erro ao gerar JSON: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return False
    
    def _build_report_structure(self) -> Dict[str, Any]:
        return {
            "metadata": self._create_metadata(),
            "executive_summary": self._generate_executive_summary(),
            "risk_assessment": self._calculate_risk_score(),
            "vulnerabilities": self._format_vulnerabilities_for_report(),
            "remediation_plan": self._generate_remediation_plan(),
            "technical_details": self._generate_technical_details(),
            "security_recommendations": self._generate_detailed_recommendations()
        }
    
    def _create_metadata(self) -> Dict[str, str]:
        return {
            "target_url": self.target_url,
            "scan_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "scanner_version": "2.0",
            "scan_duration": "Completo",
            "report_generated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def _generate_executive_summary(self) -> Dict[str, Any]:
        critical_count = len([v for v in self.vulnerabilities if v.severity == "Crítica"])
        high_count = len([v for v in self.vulnerabilities if v.severity == "Alta"])
        medium_count = len([v for v in self.vulnerabilities if v.severity == "Média"])
        low_count = len([v for v in self.vulnerabilities if v.severity == "Baixa"])
        
        return {
            "total_vulnerabilities": len(self.vulnerabilities),
            "critical_vulnerabilities": critical_count,
            "high_vulnerabilities": high_count,
            "medium_vulnerabilities": medium_count,
            "low_vulnerabilities": low_count,
            "overall_risk": "CRÍTICO" if critical_count > 0 else "ALTO" if high_count > 0 else "MODERADO",
            "key_findings": self._get_key_findings()
        }
    
    def _get_key_findings(self) -> List[str]:
        findings = []
        
        for vuln in self.vulnerabilities:
            if vuln.severity in ["Crítica", "Alta"]:
                if "SQL Injection" in vuln.type:
                    findings.append("SQL Injection crítico no sistema de autenticação")
                elif "Password" in vuln.type and "Plain Text" in vuln.type:
                    findings.append("Passwords armazenadas em plain text")
                elif "Credenciais" in vuln.type and "Hardcoded" in vuln.type:
                    findings.append("Credenciais de base de dados hardcoded")
                elif "Secret Key" in vuln.type:
                    findings.append("Secret key fraca ou padrão em uso")

        return list(set(findings))
    
    def _calculate_risk_score(self) -> Dict[str, Any]:
        critical_count = len([v for v in self.vulnerabilities if v.severity == "Crítica"])
        high_count = len([v for v in self.vulnerabilities if v.severity == "Alta"])
        medium_count = len([v for v in self.vulnerabilities if v.severity == "Média"])
        
        total_score = (critical_count * 10) + (high_count * 7) + (medium_count * 4)
        
        risk_level = "CRÍTICO" if total_score >= 15 else "ALTO" if total_score >= 8 else "MODERADO"
        
        return {
            "overall_risk_score": total_score,
            "risk_level": risk_level,
            "critical_vulnerabilities": critical_count,
            "high_vulnerabilities": high_count,
            "medium_vulnerabilities": medium_count
        }
    
    def _format_vulnerabilities_for_report(self) -> List[Dict[str, Any]]:
        formatted_vulns = []
        for vuln in self.vulnerabilities:
            print(f"Formatando vulnerabilidade para JSON: {vuln.type}")
            
            formatted_vulns.append({
                "type": vuln.type,
                "severity": vuln.severity,
                "description": vuln.description,
                "location": vuln.location,
                "cvss_score": vuln.cvss_score,
                "business_impact": vuln.business_impact,
                "payload": vuln.payload,
                "exploited": vuln.exploited,
                "code_snippet": vuln.code_snippet,
                "fixed_code_example": vuln.fixed_code_example,
                "verification_steps": vuln.verification_steps,
                "recommendation": vuln.recommendation
            })
        return formatted_vulns
    
    def _generate_remediation_plan(self) -> Dict[str, List]:
        plan = {
            "immediate_actions": [],
            "short_term_actions": [],
            "long_term_improvements": []
        }
        
        for vuln in self.vulnerabilities:
            if vuln.severity in ["Crítica", "Alta"]:
                plan["immediate_actions"].append({
                    "vulnerability": vuln.type,
                    "action": self._get_immediate_action(vuln),
                    "estimated_effort": "1-4 horas",
                    "priority": "ALTA",
                    "files_affected": self._get_affected_files(vuln.location)
                })
        
        return plan
    
    def _get_immediate_action(self, vulnerability: SecurityVulnerability) -> str:
        actions = {
            "SQL Injection Crítico": "Substituir todas as queries concatenadas por parameterized queries",
            "Passwords em Plain Text": "Implementar bcrypt para hash de passwords e atualizar registos existentes",
            "Credenciais de Base de Dados Hardcoded": "Mover credenciais para variáveis de ambiente",
            "Secret Key Fraca": "Gerar nova secret key segura e invalidar sessões existentes",
            "Falta de Validação de Input": "Implementar validação e sanitização de todos os inputs"
        }
        
        return actions.get(vulnerability.type, "Revisar e corrigir a vulnerabilidade identificada")
    
    def _get_affected_files(self, location: str) -> List[str]:
        if "app.py" in location:
            return ["app.py"]
        elif "models.py" in location:
            return ["models.py"]
        elif "config.py" in location:
            return ["config.py"]
        return ["Múltiplos ficheiros"]
    
    def _generate_technical_details(self) -> Dict[str, Any]:
        return {
            "sql_injection_analysis": {
                "vulnerable_pattern": "f-string concatenation in SQL queries",
                "risk": "Full database compromise",
                "exploitation_complexity": "Low",
                "prevention": "Parameterized queries, input validation"
            },
            "authentication_issues": {
                "password_storage": "Plain text in database",
                "session_management": "Permanent sessions enabled",
                "improvements": "bcrypt hashing, session timeouts"
            },
            "security_misconfigurations": {
                "hardcoded_secrets": "Database credentials in code",
                "weak_secret_key": "Default secret key in use",
                "remediation": "Environment variables, proper key generation"
            }
        }
    
    def _generate_detailed_recommendations(self) -> Dict[str, Any]:
        return {
            "critical_recommendations": [
                {
                    "title": "Corrigir SQL Injection Imediatamente",
                    "steps": [
                        "SUBSTITUIR: query = f\"SELECT ... WHERE username = '{username}'\"",
                        "POR: cur.execute('SELECT ... WHERE username = %s AND password = %s', (username, password))",
                        "APLICAR: A todas as queries no app.py e models.py"
                    ]
                },
                {
                    "title": "Implementar Hash de Passwords Seguro",
                    "steps": [
                        "INSTALAR: pip install bcrypt",
                        "ATUALIZAR: models.py com funções de hash seguras",
                        "MIGRAR: Passwords existentes para formato seguro"
                    ]
                }
            ],
            "configuration_improvements": [
                "USAR: Variáveis de ambiente para todas as credenciais",
                "GERAR: Nova SECRET_KEY com secrets.token_hex(32)",
                "DEFINIR: SESSION_COOKIE_SECURE = True em produção",
                "IMPLEMENTAR: Rate limiting no login"
            ],
            "development_best_practices": [
                "VALIDAR: Todos os inputs do utilizador",
                "ESCAPAR: Outputs para prevenir XSS",
                "LOGGAR: Tentativas de login falhadas",
                "AUDITAR: Regularmente o código para segurança"
            ]
        }