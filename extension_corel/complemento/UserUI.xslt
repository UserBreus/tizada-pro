<?xml version="1.0"?>
<!--
  USER PRO para CorelDRAW — COMPLEMENTO: pone la barra «TIZADA PRO» en el espacio de trabajo del usuario.
  Corel lo aplica UNA vez por espacio de trabajo (ver AppUI.xslt). Estructura de la plantilla pública
  bonus630/DockerTemplateX7 «CommandBarStaticTemplate».
-->
<xsl:stylesheet version="1.0"
				xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
				xmlns:frmwrk="Corel Framework Data"
				exclude-result-prefixes="frmwrk">
	<xsl:output method="xml" encoding="UTF-8" indent="yes"/>

	<frmwrk:uiconfig>
		<frmwrk:compositeNode xPath="/uiConfig/commandBars/commandBarData[@guid='bc3f54ed-5385-4891-8ad7-20e01814b661']"/>
		<frmwrk:compositeNode xPath="/uiConfig/frame"/>
	</frmwrk:uiconfig>

	<xsl:template match="node()|@*">
		<xsl:copy>
			<xsl:apply-templates select="node()|@*"/>
		</xsl:copy>
	</xsl:template>

	<!-- el botón adentro de la barra -->
	<xsl:template match="commandBarData[@guid='bc3f54ed-5385-4891-8ad7-20e01814b661']/toolbar">
		<xsl:copy>
			<xsl:apply-templates select="@*|node()"/>
			<xsl:if test="not(./item[@guidRef='712d37ec-1c3d-4911-9fcd-5fd9a16e42e3'])">
				<item guidRef="712d37ec-1c3d-4911-9fcd-5fd9a16e42e3"/>
			</xsl:if>
		</xsl:copy>
	</xsl:template>

	<!-- la barra, visible arriba (en el diseño del marco y en el estado guardado del espacio de trabajo) -->
	<xsl:template match="uiConfig/containers/container[@guid='bee85f91-3ad9-dc8d-48b5-d2a87c8b2109']/container[@guid='Framework_MainFrame-layout']/dockHost[@guid='894bf987-2ec1-8f83-41d8-68f6797d0db4']/toolbar[@guidRef='c2b44f69-6dec-444e-a37e-5dbf7ff43dae']">
		<xsl:copy>
			<xsl:apply-templates select="node()|@*"/>
			<xsl:if test="not(./toolbar[@guidRef='bc3f54ed-5385-4891-8ad7-20e01814b661'])">
				<toolbar guidRef="bc3f54ed-5385-4891-8ad7-20e01814b661" dock="top"/>
			</xsl:if>
		</xsl:copy>
	</xsl:template>

	<xsl:template match="uiConfig/states/state[1]/container[@guidRef='bee85f91-3ad9-dc8d-48b5-d2a87c8b2109']/layout/dockHost[@guid='894bf987-2ec1-8f83-41d8-68f6797d0db4']/toolbar[@guidRef='c2b44f69-6dec-444e-a37e-5dbf7ff43dae']">
		<xsl:copy>
			<xsl:apply-templates select="node()|@*"/>
			<xsl:if test="not(./toolbar[@guidRef='bc3f54ed-5385-4891-8ad7-20e01814b661'])">
				<toolbar guidRef="bc3f54ed-5385-4891-8ad7-20e01814b661" dock="top"/>
			</xsl:if>
		</xsl:copy>
	</xsl:template>
</xsl:stylesheet>
