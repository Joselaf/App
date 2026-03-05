import flet as ft
import tinytuya
import json
from datetime import datetime


class DeviceMonitor:
    def __init__(self, api_region, api_key, api_secret):
        self.cloud = tinytuya.Cloud(
            apiRegion=api_region,
            apiKey=api_key,
            apiSecret=api_secret
        )
    
    def get_critical_alerts(self):
        """Obtém dispositivos com situações críticas"""
        alerts = {
            'low_battery': [],
            'tripped_breakers': [],
            'panic_button': [],
            'fire_alarms': []
        }
        
        try:
            devices = self.cloud.getdevices()
            
            for device in devices:
                device_id = device.get('id')
                device_name = device.get('name', 'Sem nome')
                
                # Obter status do dispositivo
                status = self.cloud.getstatus(device_id)
                
                if status and 'result' in status:
                    dps = status['result']
                    
                    # Verificar bateria baixa (fechaduras)
                    if 'battery_percentage' in dps or 'battery_state' in dps:
                        battery = dps.get('battery_percentage', 100)
                        if battery < 20:
                            alerts['low_battery'].append({
                                'name': device_name,
                                'battery': battery,
                                'id': device_id
                            })
                    
                    # Verificar disjuntores disparados
                    if 'switch' in dps and dps.get('switch') == False:
                        if 'breaker' in device_name.lower() or 'disjuntor' in device_name.lower():
                            alerts['tripped_breakers'].append({
                                'name': device_name,
                                'id': device_id
                            })
                    
                    # Verificar botão de pânico
                    if 'panic_button' in dps or 'emergency' in dps:
                        if dps.get('panic_button') or dps.get('emergency'):
                            alerts['panic_button'].append({
                                'name': device_name,
                                'id': device_id,
                                'timestamp': datetime.now().isoformat()
                            })
                    
                    # Verificar alarmes de incêndio
                    if 'smoke_sensor_state' in dps or 'fire_alarm' in dps:
                        if dps.get('smoke_sensor_state') == 'alarm' or dps.get('fire_alarm'):
                            alerts['fire_alarms'].append({
                                'name': device_name,
                                'id': device_id,
                                'timestamp': datetime.now().isoformat()
                            })
        
        except Exception as e:
            print(f"Erro ao obter dispositivos: {e}")
        
        return alerts


def main(page: ft.Page):
    page.title = "Monitor de Dispositivos TinyTuya"
    page.padding = 20
    
    # Configurações da API (substitua com suas credenciais)
    api_region = "eu"  # ou "eu", "cn", etc.
    api_key = "c8uhx3vs89grhea8mg7p"
    api_secret = "7221603a3b754d8b89b30c8dc9114b0d"
    
    monitor = DeviceMonitor(api_region, api_key, api_secret)
    alerts_container = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
    
    def create_alert_card(title, items, icon, color):
        """Cria um card de alerta"""
        if not items:
            return None
        
        card_items = []
        for item in items:
            details = [ft.Text(f"Nome: {item['name']}", size=14)]
            
            if 'battery' in item:
                details.append(ft.Text(f"Bateria: {item['battery']}%", color=ft.Colors.RED))
            if 'timestamp' in item:
                details.append(ft.Text(f"Horário: {item['timestamp']}", size=12))
            
            card_items.append(
                ft.Container(
                    content=ft.Column(details),
                    padding=10,
                    border=ft.border.all(1, ft.Colors.GREY_400),
                    border_radius=5,
                    margin=ft.margin.only(bottom=5)
                )
            )
        
        return ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(icon, color=color, size=30),
                        ft.Text(f"{title} ({len(items)})", size=18, weight=ft.FontWeight.BOLD)
                    ]),
                    ft.Divider(),
                    ft.Column(card_items)
                ]),
                padding=15
            ),
            margin=ft.margin.only(bottom=10)
        )
    
    def refresh_alerts(e=None):
        """Atualiza a lista de alertas"""
        alerts_container.controls.clear()
        
        alerts_container.controls.append(
            ft.Text("Carregando dispositivos...", size=16, italic=True)
        )
        page.update()
        
        alerts = monitor.get_critical_alerts()
        alerts_container.controls.clear()
        
        # Bateria baixa
        battery_card = create_alert_card(
            "Fechaduras com Bateria Baixa",
            alerts['low_battery'],
            ft.Icons.BATTERY_ALERT,
            ft.Colors.ORANGE
        )
        if battery_card:
            alerts_container.controls.append(battery_card)
        
        # Disjuntores disparados
        breaker_card = create_alert_card(
            "Disjuntores Disparados",
            alerts['tripped_breakers'],
            ft.Icons.POWER_OFF,
            ft.Colors.RED
        )
        if breaker_card:
            alerts_container.controls.append(breaker_card)
        
        # Botão de pânico
        panic_card = create_alert_card(
            "Botão de Pânico Acionado",
            alerts['panic_button'],
            ft.Icons.WARNING,
            ft.Colors.RED
        )
        if panic_card:
            alerts_container.controls.append(panic_card)
        
        # Alarmes de incêndio
        fire_card = create_alert_card(
            "Alarmes de Incêndio",
            alerts['fire_alarms'],
            ft.Icons.LOCAL_FIRE_DEPARTMENT,
            ft.Colors.DEEP_ORANGE
        )
        if fire_card:
            alerts_container.controls.append(fire_card)
        
        if not any([battery_card, breaker_card, panic_card, fire_card]):
            alerts_container.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN, size=50),
                        ft.Text("Nenhum alerta crítico", size=20, weight=ft.FontWeight.BOLD)
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.alignment.center,
                    padding=50
                )
            )
        
        page.update()
    
    # Interface
    page.add(
        ft.SafeArea(
            expand=True,
            content=ft.Column([
                ft.Row([
                    ft.Text("Monitor de Dispositivos Críticos", size=24, weight=ft.FontWeight.BOLD),
                    ft.IconButton(
                        icon=ft.Icons.REFRESH,
                        tooltip="Atualizar",
                        on_click=refresh_alerts
                    )
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(),
                alerts_container
            ], expand=True)
        )
    )
    
    # Carregar alertas inicialmente
    refresh_alerts()


ft.run(main)
