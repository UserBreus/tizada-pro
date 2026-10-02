<?xml version="1.0"?>
<!--
  USER PRO para CorelDRAW — COMPLEMENTO: la barra «TIZADA PRO» con el botón «Exportar para TIZADA PRO».

  Lo copia el conector (con permiso de administrador, una vez) a
  <CorelDRAW>\Programs64\Addons\TizadaPro\ junto con `CorelDrw.addon` (vacío: «cargalo en CorelDRAW»)
  y `UserUI.xslt`. Corel lo lee al arrancar: por eso después de instalar hay que cerrar y abrir Corel.

  🔴 POR QUÉ ASÍ (probado con la 2026): Corel no deja registrar macros ni botones desde afuera (no
  expone el editor de VBA por COM y `RunMacro` no ve proyectos nuevos). Un botón común de Corel sólo
  puede usar los íconos INTERNOS de Corel: la versión 1.3.0 usaba uno desplegable y en la barra
  quedaba una flechita sola, sin texto ni ícono (queja del usuario 2026-10-01). Por eso el botón es
  un CONTROL PROPIO (`type="wpfhost"`): `TizadaPro.dll` (`BotonTizada.cs`), que dibuja el ícono de
  TIZADA PRO en verde y el texto entero, y al tocarlo le pide al conector (127.0.0.1:47851) que
  exporte. Es el mecanismo de los complementos de Corel 2022+ (plantillas públicas de bonus630:
  DockerTemplateX7 «ButtonTemplateCS2022», .NET Framework 4.8).

  Identificadores (fijos: si cambian, Corel lo toma como otro complemento):
    712d37ec-1c3d-4911-9fcd-5fd9a16e42e3 = el botón (el MISMO de la 1.3.0: así la barra que ya quedó
                                           en el espacio de trabajo muestra el botón nuevo sola)
    bc3f54ed-5385-4891-8ad7-20e01814b661 = la barra «TIZADA PRO»
-->
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:frmwrk="Corel Framework Data">
	<xsl:output method="xml" encoding="UTF-8" indent="yes"/>

	<frmwrk:uiconfig>
		<frmwrk:applicationInfo userConfiguration="true" />
	</frmwrk:uiconfig>

	<!-- Copiar todo lo demás tal cual -->
	<xsl:template match="node()|@*">
		<xsl:copy>
			<xsl:apply-templates select="node()|@*"/>
		</xsl:copy>
	</xsl:template>

	<xsl:template match="uiConfig/items">
		<xsl:copy>
			<xsl:apply-templates select="node()|@*"/>
			<!-- el botón: control propio con el ícono de TIZADA PRO y el texto (ver arriba) -->
			<itemData guid="712d37ec-1c3d-4911-9fcd-5fd9a16e42e3"
					  type="wpfhost"
					  hostedType="Addons\TizadaPro\TizadaPro.dll,UserPro.Corel.BotonTizada"
					  caption="Exportar para TIZADA PRO"
					  nonLocalizableName="Exportar para TIZADA PRO"
					  enable="true"/>
		</xsl:copy>
	</xsl:template>

	<xsl:template match="uiConfig/commandBars">
		<xsl:copy>
			<xsl:apply-templates select="node()|@*"/>
			<commandBarData guid="bc3f54ed-5385-4891-8ad7-20e01814b661"
							nonLocalizableName="TIZADA PRO"
							userCaption="TIZADA PRO"
							type="toolbar">
				<toolbar>
					<item guidRef="712d37ec-1c3d-4911-9fcd-5fd9a16e42e3" dock="top"/>
				</toolbar>
			</commandBarData>
		</xsl:copy>
	</xsl:template>

	<!-- la barra, arriba, al lado de la barra «Estándar» -->
	<xsl:template match="uiConfig/containers/container[@guid='bee85f91-3ad9-dc8d-48b5-d2a87c8b2109']/container[@guid='Framework_MainFrame-layout']/dockHost[@guid='894bf987-2ec1-8f83-41d8-68f6797d0db4']/toolbar[@guidRef='c2b44f69-6dec-444e-a37e-5dbf7ff43dae']">
		<xsl:copy-of select="."/>
		<toolbar guidRef="bc3f54ed-5385-4891-8ad7-20e01814b661" dock="top"/>
	</xsl:template>
</xsl:stylesheet>
