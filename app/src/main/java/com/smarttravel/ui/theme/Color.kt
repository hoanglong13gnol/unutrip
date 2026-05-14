package com.smarttravel.ui.theme

import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.unit.dp

/**
 * Brand palette extracted from the travel UI brief (pastel green shell, coral accents, white cards).
 * Adjust hex values here when a final design export is available.
 */
object SmartTravelPalette {
    val PastelGreen = Color(0xFFD5E8D4)
    val PastelGreenDeep = Color(0xFFBED6BC)
    val Coral = Color(0xFFF08060)
    val CoralDark = Color(0xFFE06A48)
    val White = Color(0xFFFFFFFF)
    val Charcoal = Color(0xFF1E2A3A)
    val Navy = Color(0xFF243B53)
    val GraySecondary = Color(0xFF6B7280)
    val GrayMuted = Color(0xFF9CA3AF)
    val CoralContainer = Color(0xFFFFE8E0)
    val GreenSurfaceTint = Color(0xFFE8F2E7)
    val OutlineSoft = Color(0xFFC5D4C4)
    val ScrimSoft = Color(0x33000000)
}

fun smartTravelLightColorScheme() = lightColorScheme(
    primary = SmartTravelPalette.Coral,
    onPrimary = SmartTravelPalette.White,
    primaryContainer = SmartTravelPalette.CoralContainer,
    onPrimaryContainer = SmartTravelPalette.Navy,
    secondary = SmartTravelPalette.PastelGreenDeep,
    onSecondary = SmartTravelPalette.Charcoal,
    secondaryContainer = SmartTravelPalette.GreenSurfaceTint,
    onSecondaryContainer = SmartTravelPalette.Navy,
    tertiary = SmartTravelPalette.Navy,
    onTertiary = SmartTravelPalette.White,
    tertiaryContainer = SmartTravelPalette.PastelGreen,
    onTertiaryContainer = SmartTravelPalette.Charcoal,
    background = SmartTravelPalette.PastelGreen,
    onBackground = SmartTravelPalette.Charcoal,
    surface = SmartTravelPalette.White,
    onSurface = SmartTravelPalette.Charcoal,
    surfaceVariant = SmartTravelPalette.GreenSurfaceTint,
    onSurfaceVariant = SmartTravelPalette.GraySecondary,
    outline = SmartTravelPalette.OutlineSoft,
    outlineVariant = SmartTravelPalette.PastelGreenDeep,
    error = Color(0xFFB3261E),
    onError = SmartTravelPalette.White,
)

/**
 * Optional dark scheme tuned for OLED-friendly greens; keep in sync with product direction.
 */
fun smartTravelDarkColorScheme() = darkColorScheme(
    primary = SmartTravelPalette.Coral,
    onPrimary = SmartTravelPalette.Charcoal,
    primaryContainer = SmartTravelPalette.CoralDark,
    onPrimaryContainer = SmartTravelPalette.White,
    secondary = SmartTravelPalette.PastelGreen,
    onSecondary = SmartTravelPalette.Charcoal,
    secondaryContainer = Color(0xFF2F4538),
    onSecondaryContainer = SmartTravelPalette.PastelGreen,
    tertiary = SmartTravelPalette.PastelGreenDeep,
    onTertiary = SmartTravelPalette.Charcoal,
    background = Color(0xFF102018),
    onBackground = SmartTravelPalette.White,
    surface = Color(0xFF1A2C22),
    onSurface = SmartTravelPalette.White,
    surfaceVariant = Color(0xFF24352C),
    onSurfaceVariant = SmartTravelPalette.GrayMuted,
    outline = Color(0xFF4A5E52),
)

@Composable
@Preview(showBackground = true, name = "Palette swatches")
private fun SmartTravelPalettePreview() {
    MaterialTheme(colorScheme = smartTravelLightColorScheme(), typography = smartTravelTypography()) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            SwatchRow("Pastel green", SmartTravelPalette.PastelGreen)
            SwatchRow("Coral", SmartTravelPalette.Coral)
            SwatchRow("White / surface", SmartTravelPalette.White)
            SwatchRow("Charcoal text", SmartTravelPalette.Charcoal)
            SwatchRow("Gray secondary", SmartTravelPalette.GraySecondary)
        }
    }
}

@Composable
private fun SwatchRow(label: String, color: Color) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Box(
            modifier = Modifier
                .height(40.dp)
                .weight(1f)
                .clip(RoundedCornerShape(12.dp))
                .background(color),
        )
        Text(text = label, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onBackground)
    }
}
