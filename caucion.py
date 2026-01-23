"""
Caucion
Módulo para el cálculo de caución (tasas de interés) en operaciones de arbitraje de plazos.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Caucion:
    """
    Representa el cálculo de una caución (colocadora o tomadora).
    
    Attributes:
        dias: Días de la caución (negativo = colocadora, positivo = tomadora)
        tna: Tasa Nominal Anual (%)
        importe_bruto: Monto total a caucionar
        arancel_tna: Tasa de arancel del broker (%)
    """
    
    # Constantes según BYMA
    # https://www.byma.com.ar/que-es-byma/derechos-membresias-2/
    DERECHOS_MERCADO_TASA_DIARIA = 0.045 / 100 / 90
    GASTOS_GARANTIA_TASA_DIARIA = 0.045 / 100 / 90
    IVA_PORCENTAJE = 0.21
    
    def __init__(
        self,
        dias: int,
        tna: float,
        importe_bruto: float,
        arancel_tomadora: float = 10.0,
        arancel_colocadora: float = 10.0
    ):
        """
        Inicializa el cálculo de caución.
        
        Args:
            dias: Días de la caución (negativo = colocadora, positivo = tomadora)
            tna: Tasa Nominal Anual en porcentaje (ej: 35.0 para 35%)
            importe_bruto: Monto a caucionar
            arancel_tomadora: TNA del arancel del broker para caución tomadora (%)
            arancel_colocadora: TNA del arancel del broker para caución colocadora (%)
        """
        self.dias = dias
        self.tna = tna
        self.importe_bruto = importe_bruto
        
        dias_abs = abs(dias)
        
        # Calcular tasa proporcional a los días
        self.tasa = abs(tna / 100 * dias_abs / 365)
        
        # Determinar tipo de caución
        self.es_colocadora = dias < 0
        
        # Arancel según tipo de caución
        self.arancel_tna = arancel_colocadora if self.es_colocadora else arancel_tomadora
        
        # Cálculo de interés
        self.interes = importe_bruto * self.tasa
        self.importe_con_interes = importe_bruto + self.interes
        
        # Cálculo de gastos
        self.arancel = self.importe_con_interes * (self.arancel_tna / 100 * dias_abs / 365)
        self.derechos_mercado = self.importe_con_interes * self.DERECHOS_MERCADO_TASA_DIARIA * dias_abs
        
        # Gastos de garantía solo para tomadora
        self.gastos_garantia = (
            0 if self.es_colocadora
            else self.importe_con_interes * self.GASTOS_GARANTIA_TASA_DIARIA * dias_abs
        )
        
        # Total de gastos
        self.gastos = self.arancel + self.derechos_mercado + self.gastos_garantia
        self.iva_gastos = self.gastos * self.IVA_PORCENTAJE
        self.total_gastos = self.gastos + self.iva_gastos
        
        # Interés neto (después de gastos)
        if self.es_colocadora:
            # Colocadora: gano interés pero pago gastos
            self.interes_neto = self.interes - self.total_gastos
            self.importe_neto = self.importe_con_interes - self.total_gastos
        else:
            # Tomadora: pago interés y gastos
            self.interes_neto = self.interes + self.total_gastos
            self.importe_neto = self.importe_con_interes + self.total_gastos
    
    def __repr__(self) -> str:
        tipo = "Colocadora" if self.es_colocadora else "Tomadora"
        return (
            f"Caucion({tipo}, dias={abs(self.dias)}, tna={self.tna:.2f}%, "
            f"interes_neto=${self.interes_neto:,.2f})"
        )
