import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Notificação do Sistema</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f5f5f7; -webkit-font-smoothing: antialiased;">

    <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #f5f5f7; padding: 40px 20px;">
        <tr>
            <td align="center">

                <table width="100%" max-width="600" border="0" cellspacing="0" cellpadding="0" style="max-width: 600px; background-color: #ffffff; border-radius: 18px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.04);">

                    <tr>
                        <td style="padding: 30px 40px; border-bottom: 1px solid #d2d2d7; text-align: right;">
                            <img src="https://www.fattocs.com/wp-content/uploads/2020/07/logo_fatto_1.png" alt="FATTO Consultoria e Sistemas" style="height: 50pt; width: auto; display: inline-block; border: none; outline: none;">
                        </td>
                    </tr>

                    <tr>
                        <td style="padding: 40px;">
                            <h1 style="margin: 0 0 20px 0; font-size: 28px; font-weight: 600; color: #1d1d1f; letter-spacing: -0.02em;">Aviso do Sistema</h1>

                            <p style="margin: 0 0 24px 0; font-size: 17px; line-height: 1.5; color: #515154;">
                                Identificamos que um plugin foi desabilitado em seu ambiente WordPress. Abaixo estão os detalhes para sua análise e registro técnico.
                            </p>

                            <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #f5f5f7; border-radius: 12px; margin-bottom: 30px;">
                                <tr>
                                    <td style="padding: 24px;">
                                        <h2 style="margin: 0 0 16px 0; font-size: 14px; font-weight: 600; color: #86868b; text-transform: uppercase; letter-spacing: 0.05em;">Detalhes do Plugin</h2>

                                        <table width="100%" border="0" cellspacing="0" cellpadding="0" style="font-size: 15px; line-height: 1.6; color: #1d1d1f;">
                                            <tr>
                                                <td width="35%" style="padding-bottom: 8px; font-weight: 500; color: #515154;">Nome do Plugin:</td>
                                                <td style="padding-bottom: 8px; font-weight: 600;">{plugin_name}</td>
                                            </tr>
                                            <tr>
                                                <td style="padding-bottom: 8px; font-weight: 500; color: #515154;">Versão:</td>
                                                <td style="padding-bottom: 8px;">{plugin_version}</td>
                                            </tr>
                                            <tr>
                                                <td style="padding-bottom: 8px; font-weight: 500; color: #515154;">Diretório:</td>
                                                <td style="padding-bottom: 8px; font-family: monospace; color: #0071e3;">/wp-content/plugins/{plugin_dir}</td>
                                            </tr>
                                            <tr>
                                                <td style="padding-bottom: 8px; font-weight: 500; color: #515154;">Motivo:</td>
                                                <td style="padding-bottom: 8px;">{reason}</td>
                                            </tr>
                                            <tr>
                                                <td style="padding-bottom: 0; font-weight: 500; color: #515154;">Data/Hora:</td>
                                                <td style="padding-bottom: 0;">{timestamp}</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>

                            <p style="margin: 0 0 30px 0; font-size: 15px; line-height: 1.5; color: #515154;">
                                Recomendamos verificar o painel administrativo ou os logs de erro do servidor para garantir que a estabilidade do site não foi afetada.
                            </p>

                            <table width="100%" border="0" cellspacing="0" cellpadding="0">
                                <tr>
                                    <td align="center">
                                        <a href="{wp_admin_url}" style="display: inline-block; padding: 14px 28px; background-color: #0071e3; color: #ffffff; text-decoration: none; border-radius: 980px; font-size: 16px; font-weight: 600; letter-spacing: -0.01em;">Acessar Painel WordPress</a>
                                    </td>
                                </tr>
                            </table>

                        </td>
                    </tr>

                    <tr>
                        <td style="padding: 30px 40px; background-color: #fafafa; border-top: 1px solid #e5e5ea; text-align: center;">
                            <p style="margin: 0 0 10px 0; font-size: 12px; color: #86868b; line-height: 1.4;">
                                Esta é uma mensagem automática gerada pelo sistema de monitoramento.<br>
                                Por favor, não responda a este e-mail.
                            </p>
                            <p style="margin: 0; font-size: 12px; color: #86868b; font-weight: 500;">
                                &copy; 2026 FATTO Consultoria e Sistemas. Todos os direitos reservados.
                            </p>
                        </td>
                    </tr>

                </table>
                </td>
        </tr>
    </table>

</body>
</html>
"""

def send_plugin_notification(smtp_config, plugin_data, success=True):
    """
    Sends an email notification using SMTP.
    smtp_config: dict with host, port, user, pass, ssl, sender_name, receiver, cc
    plugin_data: dict with name, version, dir, reason, timestamp, wp_admin_url
    success: bool indicating if reactivation was successful
    """
    try:
        subject = "Notificação de Plugin WordPress - " + plugin_data.get('name', 'Plugin')
        if not success:
            subject = "*** URGENTE *** " + subject

        msg = MIMEMultipart()
        msg['From'] = f"{smtp_config['sender_name']} <{smtp_config['user']}>"
        msg['To'] = smtp_config['receiver']
        if smtp_config.get('cc'):
            msg['Cc'] = smtp_config['cc']
        msg['Subject'] = subject

        body = HTML_TEMPLATE.format(
            plugin_name=plugin_data.get('name', 'N/A'),
            plugin_version=plugin_data.get('version', 'N/A'),
            plugin_dir=plugin_data.get('dir', 'N/A'),
            reason=plugin_data.get('reason', 'N/A'),
            timestamp=plugin_data.get('timestamp', datetime.now().strftime("%d/%m/%Y às %H:%M")),
            wp_admin_url=plugin_data.get('wp_admin_url', '#')
        )
        msg.attach(MIMEText(body, 'html'))

        recipients = [smtp_config['receiver']]
        if smtp_config.get('cc'):
            recipients.append(smtp_config['cc'])

        if smtp_config['ssl']:
            server = smtplib.SMTP_SSL(smtp_config['host'], smtp_config['port'])
        else:
            server = smtplib.SMTP(smtp_config['host'], smtp_config['port'])
            server.starttls()

        server.login(smtp_config['user'], smtp_config['pass'])
        server.sendmail(smtp_config['user'], recipients, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False
