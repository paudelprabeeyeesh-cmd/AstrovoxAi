package ai.astrovox.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val DarkColorScheme = darkColorScheme(
    primary = Color(0xFF06B6D4),
    secondary = Color(0xFF0EA5E9),
    background = Color(0xFF0F1115),
    surface = Color(0xFF14171D),
    onPrimary = Color(0xFF0B1220),
    onSecondary = Color(0xFF0B1220),
    onBackground = Color(0xFFE6E8EB),
    onSurface = Color(0xFFE6E8EB)
)

private val LightColorScheme = lightColorScheme(
    primary = Color(0xFF06B6D4),
    secondary = Color(0xFF0EA5E9),
    background = Color(0xFFF8FAFC),
    surface = Color(0xFFFFFFFF),
    onPrimary = Color.White,
    onSecondary = Color.White,
    onBackground = Color(0xFF0F172A),
    onSurface = Color(0xFF0F172A)
)

@Composable
fun AstrovoxAITheme(darkTheme: Boolean = isSystemInDarkTheme(), content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = if (darkTheme) DarkColorScheme else LightColorScheme,
        typography = Typography(),
        content = content
    )
}
