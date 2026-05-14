package com.smarttravel.ui.theme

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CornerBasedShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp

/**
 * Corner radii tuned for soft, card-heavy layouts (16–24dp+).
 */
object SmartTravelShapeTokens {
    val RadiusXs = 12.dp
    val RadiusSm = 16.dp
    val RadiusMd = 20.dp
    val RadiusLg = 24.dp
    val RadiusXl = 28.dp
}

val smartTravelShapes = Shapes(
    extraSmall = RoundedCornerShape(SmartTravelShapeTokens.RadiusXs),
    small = RoundedCornerShape(SmartTravelShapeTokens.RadiusSm),
    medium = RoundedCornerShape(SmartTravelShapeTokens.RadiusMd),
    large = RoundedCornerShape(SmartTravelShapeTokens.RadiusLg),
    extraLarge = RoundedCornerShape(SmartTravelShapeTokens.RadiusXl),
)

@Composable
@Preview(showBackground = true, name = "Shape tokens")
private fun SmartTravelShapesPreview() {
    MaterialTheme(
        colorScheme = smartTravelLightColorScheme(),
        typography = smartTravelTypography(),
        shapes = smartTravelShapes,
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text("Material shapes → cards & fields", style = MaterialTheme.typography.titleMedium)
            BoxWithConstraints(modifier = Modifier.fillMaxWidth()) {
                val gap = 8.dp
                val w3 = (maxWidth - gap * 2) / 3
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(gap),
                ) {
                    ShapeChip("extraSmall", MaterialTheme.shapes.extraSmall, Modifier.width(w3))
                    ShapeChip("small", MaterialTheme.shapes.small, Modifier.width(w3))
                    ShapeChip("medium", MaterialTheme.shapes.medium, Modifier.width(w3))
                }
            }
            BoxWithConstraints(modifier = Modifier.fillMaxWidth()) {
                val gap = 8.dp
                val w2 = (maxWidth - gap) / 2
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(gap),
                ) {
                    ShapeChip("large", MaterialTheme.shapes.large, Modifier.width(w2))
                    ShapeChip("extraLarge", MaterialTheme.shapes.extraLarge, Modifier.width(w2))
                }
            }
        }
    }
}

@Composable
private fun ShapeChip(label: String, shape: CornerBasedShape, modifier: Modifier = Modifier) {
    Surface(
        modifier = modifier.height(56.dp),
        shape = shape,
        tonalElevation = 2.dp,
        shadowElevation = 2.dp,
        color = MaterialTheme.colorScheme.surface,
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .clip(shape)
                .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.12f)),
            contentAlignment = Alignment.Center,
        ) {
            Text(text = label, style = MaterialTheme.typography.labelMedium)
        }
    }
}
