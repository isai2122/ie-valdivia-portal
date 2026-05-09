"""
Generador de reportes PDF profesionales para MetanoSRGAN Elite
Integra datos reales de detecciones con visualizaciones y análisis
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict
import json
from pathlib import Path
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from io import BytesIO
import base64


class ReportGenerator:
    """Generador de reportes PDF con datos reales de Sentinel-5P TROPOMI"""

    def __init__(self, data_dir: str = "/home/ubuntu/metanosrgan_v50/backend/data"):
        self.data_dir = Path(data_dir)
        self.events_file = self.data_dir / "events_real.json"
        self.events = self._load_events()
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _load_events(self) -> List[Dict]:
        """Cargar eventos reales del archivo JSON"""
        try:
            with open(self.events_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error cargando eventos: {e}")
            return []

    def _setup_custom_styles(self):
        """Configurar estilos personalizados para el reporte"""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a472a'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))

        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#2d5a3d'),
            spaceAfter=12,
            fontName='Helvetica-Bold'
        ))

        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['BodyText'],
            fontSize=10,
            alignment=TA_JUSTIFY,
            spaceAfter=12
        ))

    def _get_station_stats(self, station: str) -> Dict:
        """Calcular estadísticas para una estación"""
        station_events = [e for e in self.events if e.get('station') == station]
        if not station_events:
            return {}

        ppbs = [e.get('ppb', 0) for e in station_events]
        return {
            'count': len(station_events),
            'avg_ppb': sum(ppbs) / len(ppbs),
            'max_ppb': max(ppbs),
            'min_ppb': min(ppbs),
            'critical_count': len([p for p in ppbs if p > 2300]),
            'high_count': len([p for p in ppbs if 2200 < p <= 2300]),
        }

    def _create_summary_chart(self) -> str:
        """Crear gráfico de resumen de eventos por estación"""
        stations = {}
        for event in self.events:
            station = event.get('station', 'Unknown')
            stations[station] = stations.get(station, 0) + 1

        fig, ax = plt.subplots(figsize=(8, 4))
        ax.bar(stations.keys(), stations.values(), color='#2d5a3d', edgecolor='#1a472a', linewidth=1.5)
        ax.set_ylabel('Número de Detecciones', fontsize=10, fontweight='bold')
        ax.set_xlabel('Estación', fontsize=10, fontweight='bold')
        ax.set_title('Distribución de Eventos por Estación', fontsize=12, fontweight='bold')
        ax.grid(axis='y', alpha=0.3)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()

        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        plt.close()

        return buffer

    def _create_intensity_chart(self) -> str:
        """Crear gráfico de distribución de intensidades (PPB)"""
        ppbs = [e.get('ppb', 0) for e in self.events]

        fig, ax = plt.subplots(figsize=(8, 4))
        ax.hist(ppbs, bins=20, color='#FF6B6B', edgecolor='#C92A2A', alpha=0.7)
        ax.axvline(sum(ppbs) / len(ppbs), color='#2d5a3d', linestyle='--', linewidth=2, label=f'Promedio: {sum(ppbs) / len(ppbs):.0f} ppb')
        ax.set_xlabel('Concentración de Metano (ppb)', fontsize=10, fontweight='bold')
        ax.set_ylabel('Frecuencia', fontsize=10, fontweight='bold')
        ax.set_title('Distribución de Concentraciones de Metano', fontsize=12, fontweight='bold')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        plt.tight_layout()

        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        plt.close()

        return buffer

    def generate_executive_report(self, output_path: str = None) -> bytes:
        """Generar reporte ejecutivo completo en PDF"""
        if not output_path:
            output_path = f"/tmp/MetanoSRGAN_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        doc = SimpleDocTemplate(output_path, pagesize=letter,
                                rightMargin=0.5*inch, leftMargin=0.5*inch,
                                topMargin=0.75*inch, bottomMargin=0.75*inch)

        story = []

        # Título
        story.append(Paragraph("MetanoSRGAN Elite v5.0", self.styles['CustomTitle']))
        story.append(Paragraph("Reporte Ejecutivo de Detecciones de Metano", self.styles['CustomHeading']))
        story.append(Spacer(1, 0.3*inch))

        # Información del reporte
        report_date = datetime.now().strftime("%d de %B de %Y, %H:%M:%S")
        story.append(Paragraph(f"<b>Fecha del Reporte:</b> {report_date}", self.styles['CustomBody']))
        story.append(Paragraph(f"<b>Fuente de Datos:</b> Sentinel-5P TROPOMI", self.styles['CustomBody']))
        story.append(Paragraph(f"<b>Región:</b> Magdalena Medio, Colombia", self.styles['CustomBody']))
        story.append(Spacer(1, 0.2*inch))

        # Resumen ejecutivo
        total_events = len(self.events)
        avg_ppb = sum([e.get('ppb', 0) for e in self.events]) / total_events if total_events > 0 else 0
        max_ppb = max([e.get('ppb', 0) for e in self.events]) if self.events else 0
        critical_events = len([e for e in self.events if e.get('ppb', 0) > 2300])

        story.append(Paragraph("<b>Resumen Ejecutivo</b>", self.styles['CustomHeading']))
        summary_data = [
            ['Métrica', 'Valor'],
            ['Total de Detecciones', str(total_events)],
            ['Concentración Promedio (ppb)', f'{avg_ppb:.2f}'],
            ['Concentración Máxima (ppb)', f'{max_ppb:.2f}'],
            ['Eventos Críticos (>2300 ppb)', str(critical_events)],
        ]
        summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d5a3d')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 0.3*inch))

        # Gráficos
        story.append(Paragraph("<b>Análisis Visual</b>", self.styles['CustomHeading']))

        # Gráfico de estaciones
        chart1 = self._create_summary_chart()
        img1 = Image(chart1, width=6*inch, height=3*inch)
        story.append(img1)
        story.append(Spacer(1, 0.2*inch))

        # Gráfico de intensidades
        chart2 = self._create_intensity_chart()
        img2 = Image(chart2, width=6*inch, height=3*inch)
        story.append(img2)
        story.append(PageBreak())

        # Estadísticas por estación
        story.append(Paragraph("<b>Estadísticas Detalladas por Estación</b>", self.styles['CustomHeading']))

        stations = ['Vasconia', 'Mariquita', 'Barrancabermeja', 'Malena', 'Miraflores']
        station_data = [['Estación', 'Eventos', 'PPB Promedio', 'PPB Máximo', 'Críticos']]

        for station in stations:
            stats = self._get_station_stats(station)
            if stats:
                station_data.append([
                    station,
                    str(stats.get('count', 0)),
                    f"{stats.get('avg_ppb', 0):.1f}",
                    f"{stats.get('max_ppb', 0):.1f}",
                    str(stats.get('critical_count', 0))
                ])

        station_table = Table(station_data, colWidths=[1.5*inch, 1*inch, 1.5*inch, 1.5*inch, 1*inch])
        station_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d5a3d')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        story.append(station_table)
        story.append(Spacer(1, 0.3*inch))

        # Conclusiones
        story.append(Paragraph("<b>Conclusiones y Recomendaciones</b>", self.styles['CustomHeading']))
        conclusions = f"""
        <b>Hallazgos Principales:</b><br/>
        • Se detectaron {total_events} eventos de metano en el Magdalena Medio<br/>
        • La concentración promedio fue de {avg_ppb:.1f} ppb<br/>
        • Se registraron {critical_events} eventos en nivel crítico (>2300 ppb)<br/>
        • Las estaciones más activas fueron Malena y Vasconia<br/>
        <br/>
        <b>Recomendaciones:</b><br/>
        • Aumentar la frecuencia de monitoreo en estaciones críticas<br/>
        • Implementar medidas de control en fugas identificadas<br/>
        • Continuar con la vigilancia geoespacial mediante Sentinel-5P<br/>
        • Integrar datos con sistemas de gestión ambiental existentes
        """
        story.append(Paragraph(conclusions, self.styles['CustomBody']))

        # Pie de página
        story.append(Spacer(1, 0.3*inch))
        footer = f"<i>Reporte generado por MetanoSRGAN Elite v5.0 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>"
        story.append(Paragraph(footer, self.styles['Normal']))

        # Generar PDF
        doc.build(story)

        # Leer el archivo y retornar como bytes
        with open(output_path, 'rb') as f:
            pdf_bytes = f.read()

        return pdf_bytes

    def generate_station_report(self, station: str) -> bytes:
        """Generar reporte detallado para una estación específica"""
        output_path = f"/tmp/MetanoSRGAN_Report_{station}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        doc = SimpleDocTemplate(output_path, pagesize=letter,
                                rightMargin=0.5*inch, leftMargin=0.5*inch,
                                topMargin=0.75*inch, bottomMargin=0.75*inch)

        story = []

        # Título
        story.append(Paragraph(f"Reporte de Estación: {station}", self.styles['CustomTitle']))
        story.append(Spacer(1, 0.2*inch))

        # Estadísticas
        stats = self._get_station_stats(station)
        story.append(Paragraph("<b>Estadísticas de la Estación</b>", self.styles['CustomHeading']))

        stats_data = [
            ['Métrica', 'Valor'],
            ['Total de Detecciones', str(stats.get('count', 0))],
            ['Concentración Promedio', f"{stats.get('avg_ppb', 0):.2f} ppb"],
            ['Concentración Máxima', f"{stats.get('max_ppb', 0):.2f} ppb"],
            ['Concentración Mínima', f"{stats.get('min_ppb', 0):.2f} ppb"],
            ['Eventos Críticos', str(stats.get('critical_count', 0))],
            ['Eventos Altos', str(stats.get('high_count', 0))],
        ]

        stats_table = Table(stats_data, colWidths=[3*inch, 2*inch])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d5a3d')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(stats_table)

        # Generar PDF
        doc.build(story)

        with open(output_path, 'rb') as f:
            pdf_bytes = f.read()

        return pdf_bytes
