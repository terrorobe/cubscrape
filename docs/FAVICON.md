# Favicon Generation

This project uses `resvg` for high-quality favicon generation from SVG sources.

## Prerequisites

Install `resvg` via Homebrew:
```bash
brew install resvg
```

## Source File

The master favicon source is `public/favicon.svg` which contains:
- Purple-to-blue gradient background (`#8B5CF6` → `#3B82F6`)
- Dark mode support (lighter gradient for dark themes)
- Optically-centered play triangle at coordinates `points="11.5,9 11.5,23 23.5,16"`

## Regenerating All Favicons

To regenerate all favicon sizes after modifying `public/favicon.svg`:

```bash
# Generate PNG favicons with resvg (preserves gradients and quality)
resvg public/favicon.svg --width 16 --height 16 public/favicon-16x16.png
resvg public/favicon.svg --width 32 --height 32 public/favicon-32x32.png
resvg public/favicon.svg --width 180 --height 180 public/apple-touch-icon.png
resvg public/favicon.svg --width 192 --height 192 public/android-chrome-192x192.png
resvg public/favicon.svg --width 512 --height 512 public/android-chrome-512x512.png

# Generate multi-size ICO file (using resvg PNGs for better quality)
resvg public/favicon.svg --width 32 --height 32 /tmp/favicon-32.png
resvg public/favicon.svg --width 16 --height 16 /tmp/favicon-16.png
magick /tmp/favicon-16.png /tmp/favicon-32.png public/favicon.ico
```

## Design Notes

- **Optical Centering**: The play triangle is positioned 1.5 units right of mathematical center for proper visual balance
- **Small Size Optimization**: Triangle proportions (12:14 width-to-height) optimized for 16x16 clarity
- **Gradient Preservation**: Use `resvg` instead of ImageMagick for PNG generation to maintain color gradients
- **Dark Mode**: SVG includes `@media (prefers-color-scheme: dark)` support, but this only works in SVG contexts, not PNGs

## Quality Comparison

- **resvg**: Excellent gradient rendering, subpixel antialiasing, recommended for all formats
- **resvg → ImageMagick ICO**: Generate PNGs with resvg first, then combine into ICO for best quality
- **ImageMagick direct SVG**: Poor gradient support, avoid for primary generation
- **Browser rendering**: SVG shows full gradient and dark mode support

## Testing

View all favicon variants in the test page: `favicon-test/comparison.html`