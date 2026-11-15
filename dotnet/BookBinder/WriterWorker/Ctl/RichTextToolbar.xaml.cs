using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Runtime.InteropServices;
using System.Threading;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Documents;
using System.Windows.Input;
using System.Windows.Media;
using WriterWorker.Themes;

namespace WriterWorker.Ctl;

/// <summary>
/// Word-style formatting toolbar for the <see cref="RichTextBox"/> given by <see cref="Target"/>:
/// clipboard, font family/size, bold/italic/underline/strikethrough, font and highlight colour,
/// alignment, lists, indentation and clear-formatting.
/// </summary>
public partial class RichTextToolbar : UserControl
{
    public static readonly DependencyProperty TargetProperty = DependencyProperty.Register(
        nameof(Target),
        typeof(RichTextBox),
        typeof(RichTextToolbar),
        new PropertyMetadata(null, OnTargetChanged));

    private static readonly double[] SizePresets = [8, 9, 10, 11, 12, 14, 16, 18, 20, 22, 24, 28, 32, 36, 48, 72];

    // Enumerating installed fonts is slow, so it is done once per process and shared by every toolbar.
    private static readonly Lazy<IReadOnlyList<FontFamily>> SystemFontFamilyList = new(
        () => Fonts.SystemFontFamilies
            .OrderBy(family => family.Source, StringComparer.CurrentCultureIgnoreCase)
            .ToList(),
        LazyThreadSafetyMode.ExecutionAndPublication);

    private static readonly Lazy<IReadOnlyList<Brush>> ColorPalette = new(
        () => BuildPalette(),
        LazyThreadSafetyMode.ExecutionAndPublication);

    private static readonly Color[] BaseColors =
    [
        Color.FromRgb(0xC0, 0x00, 0x00), Color.FromRgb(0xFF, 0x00, 0x00), Color.FromRgb(0xFF, 0xC0, 0x00),
        Color.FromRgb(0xFF, 0xFF, 0x00), Color.FromRgb(0x92, 0xD0, 0x50), Color.FromRgb(0x00, 0xB0, 0x50),
        Color.FromRgb(0x00, 0xB0, 0xF0), Color.FromRgb(0x00, 0x70, 0xC0), Color.FromRgb(0x00, 0x20, 0x60),
        Color.FromRgb(0x70, 0x30, 0xA0),
    ];

    private bool _syncing;
    private bool _syncingSize;
    private Brush _fontColor = Brushes.Black;
    private Brush _highlight = Brushes.Transparent;

    public RichTextToolbar()
    {
        InitializeComponent();
        BookTheme.Ensure(this);
        FontSizeBox.ItemsSource = SizePresets
            .Select(size => size.ToString("0.#", CultureInfo.InvariantCulture))
            .ToList();
        FontColorPalette.ItemsSource = ColorPalette.Value;
        HighlightPalette.ItemsSource = ColorPalette.Value;
        UpdateSwatches();
    }

    /// <summary>The editor this toolbar formats. Usually bound to the hosting page's RichTextBox.</summary>
    public RichTextBox? Target
    {
        get => (RichTextBox?)GetValue(TargetProperty);
        set => SetValue(TargetProperty, value);
    }

    private static void OnTargetChanged(DependencyObject d, DependencyPropertyChangedEventArgs e)
    {
        var toolbar = (RichTextToolbar)d;

        if (e.OldValue is RichTextBox previous)
        {
            previous.SelectionChanged -= toolbar.OnTargetSelectionChanged;
            previous.TextChanged -= toolbar.OnTargetTextChanged;
        }

        if (e.NewValue is RichTextBox editor)
        {
            editor.SelectionChanged += toolbar.OnTargetSelectionChanged;
            editor.TextChanged += toolbar.OnTargetTextChanged;
        }

        toolbar.RefreshState();
    }

    private void OnTargetSelectionChanged(object sender, RoutedEventArgs e) => RefreshState();

    private void OnTargetTextChanged(object sender, TextChangedEventArgs e) => RefreshState();

    private static IReadOnlyList<Brush> BuildPalette()
    {
        var colors = new List<Color>();
        foreach (var value in new byte[] { 0, 38, 64, 89, 115, 140, 166, 191, 217, 255 })
        {
            colors.Add(Color.FromRgb(value, value, value));
        }

        foreach (var tint in new[] { 1.0, 0.75, 0.5, 0.25, 0.1 })
        {
            colors.AddRange(BaseColors.Select(color => Blend(color, tint)));
        }

        return colors
            .Select(color =>
            {
                var brush = new SolidColorBrush(color);
                brush.Freeze();
                return (Brush)brush;
            })
            .ToList();
    }

    private static Color Blend(Color color, double factor)
        => Color.FromRgb(
            (byte)Math.Round(color.R * factor + 255 * (1 - factor)),
            (byte)Math.Round(color.G * factor + 255 * (1 - factor)),
            (byte)Math.Round(color.B * factor + 255 * (1 - factor)));

    private void UpdateSwatches()
    {
        FontColorBar.Background = _fontColor;
        HighlightBar.Background = _highlight;
    }

    /// <summary>Mirrors the formatting at the caret into the toolbar controls.</summary>
    private void RefreshState()
    {
        var editor = Target;
        if (editor is null || _syncing)
        {
            return;
        }

        _syncing = true;
        try
        {
            var selection = editor.Selection;

            var family = selection.GetPropertyValue(TextElement.FontFamilyProperty) as FontFamily ?? editor.FontFamily;
            FontFamilyBox.Text = family.Source;

            var size = selection.GetPropertyValue(TextElement.FontSizeProperty);
            _syncingSize = true;
            FontSizeBox.Text = size is double fontSize
                ? fontSize.ToString("0.#", CultureInfo.CurrentCulture)
                : editor.FontSize.ToString("0.#", CultureInfo.CurrentCulture);
            _syncingSize = false;

            BoldButton.IsChecked = selection.GetPropertyValue(TextElement.FontWeightProperty) is FontWeight weight
                && weight.ToOpenTypeWeight() >= 600;

            ItalicButton.IsChecked = selection.GetPropertyValue(TextElement.FontStyleProperty) is FontStyle style
                && (style == FontStyles.Italic || style == FontStyles.Oblique);

            var decorations = selection.GetPropertyValue(Inline.TextDecorationsProperty) as TextDecorationCollection;
            UnderlineButton.IsChecked = HasDecoration(decorations, TextDecorationLocation.Underline);
            StrikeButton.IsChecked = HasDecoration(decorations, TextDecorationLocation.Strikethrough);

            var alignment = selection.GetPropertyValue(Block.TextAlignmentProperty) is TextAlignment value
                ? value
                : TextAlignment.Left;
            AlignLeftButton.IsChecked = alignment == TextAlignment.Left;
            AlignCenterButton.IsChecked = alignment == TextAlignment.Center;
            AlignRightButton.IsChecked = alignment == TextAlignment.Right;
            AlignJustifyButton.IsChecked = alignment == TextAlignment.Justify;

            UndoButton.IsEnabled = editor.CanUndo;
            RedoButton.IsEnabled = editor.CanRedo;
            CutButton.IsEnabled = CopyButton.IsEnabled = !selection.IsEmpty;
            PasteButton.IsEnabled = ClipboardHasText();
        }
        finally
        {
            _syncing = false;
        }
    }

    private static bool HasDecoration(TextDecorationCollection? decorations, TextDecorationLocation location)
        => decorations is not null && decorations.Any(decoration => decoration.Location == location);

    private static bool ClipboardHasText()
    {
        try
        {
            return Clipboard.ContainsText() || Clipboard.ContainsData(DataFormats.Rtf);
        }
        catch (COMException)
        {
            return false;
        }
        catch (ThreadStateException)
        {
            return false;
        }
    }

    private void RunEditingCommand(RoutedUICommand command)
    {
        var editor = Target;
        if (editor is null)
        {
            return;
        }

        editor.Focus();
        command.Execute(null, editor);
        RefreshState();
    }

    private void ApplyProperty(DependencyProperty property, object? value)
    {
        var editor = Target;
        if (editor is null)
        {
            return;
        }

        editor.Selection.ApplyPropertyValue(property, value);
        RefreshState();
    }

    private void Bold_Click(object sender, RoutedEventArgs e)
    {
        if (!_syncing)
        {
            RunEditingCommand(EditingCommands.ToggleBold);
        }
    }

    private void Italic_Click(object sender, RoutedEventArgs e)
    {
        if (!_syncing)
        {
            RunEditingCommand(EditingCommands.ToggleItalic);
        }
    }

    private void Underline_Click(object sender, RoutedEventArgs e)
    {
        if (!_syncing)
        {
            RunEditingCommand(EditingCommands.ToggleUnderline);
        }
    }

    private void Strike_Click(object sender, RoutedEventArgs e)
    {
        var editor = Target;
        if (_syncing || editor is null)
        {
            return;
        }

        var current = editor.Selection.GetPropertyValue(Inline.TextDecorationsProperty) as TextDecorationCollection;
        var struck = HasDecoration(current, TextDecorationLocation.Strikethrough);
        var next = new TextDecorationCollection();

        if (current is not null)
        {
            foreach (var decoration in current.Where(decoration => decoration.Location != TextDecorationLocation.Strikethrough))
            {
                next.Add(decoration);
            }
        }

        if (!struck)
        {
            foreach (var decoration in TextDecorations.Strikethrough)
            {
                next.Add(decoration);
            }
        }

        editor.Selection.ApplyPropertyValue(Inline.TextDecorationsProperty, next);
        editor.Focus();
        RefreshState();
    }

    private void Align_Click(object sender, RoutedEventArgs e)
    {
        if (_syncing)
        {
            return;
        }

        var alignment = sender switch
        {
            _ when ReferenceEquals(sender, AlignCenterButton) => TextAlignment.Center,
            _ when ReferenceEquals(sender, AlignRightButton) => TextAlignment.Right,
            _ when ReferenceEquals(sender, AlignJustifyButton) => TextAlignment.Justify,
            _ => TextAlignment.Left
        };

        ApplyProperty(Block.TextAlignmentProperty, alignment);
        Target?.Focus();
    }

    private void Bullets_Click(object sender, RoutedEventArgs e)
    {
        if (!_syncing)
        {
            RunEditingCommand(EditingCommands.ToggleBullets);
        }
    }

    private void Numbering_Click(object sender, RoutedEventArgs e)
    {
        if (!_syncing)
        {
            RunEditingCommand(EditingCommands.ToggleNumbering);
        }
    }

    private void Indent_Click(object sender, RoutedEventArgs e)
    {
        if (!_syncing)
        {
            RunEditingCommand(EditingCommands.IncreaseIndentation);
        }
    }

    private void Outdent_Click(object sender, RoutedEventArgs e)
    {
        if (!_syncing)
        {
            RunEditingCommand(EditingCommands.DecreaseIndentation);
        }
    }

    private void ClearFormatting_Click(object sender, RoutedEventArgs e)
    {
        var editor = Target;
        if (_syncing || editor is null)
        {
            return;
        }

        var range = new TextRange(editor.Selection.Start, editor.Selection.End);
        range.ApplyPropertyValue(TextElement.FontFamilyProperty, editor.FontFamily);
        range.ApplyPropertyValue(TextElement.FontSizeProperty, editor.FontSize);
        range.ApplyPropertyValue(TextElement.FontWeightProperty, FontWeights.Normal);
        range.ApplyPropertyValue(TextElement.FontStyleProperty, FontStyles.Normal);
        range.ApplyPropertyValue(Inline.TextDecorationsProperty, new TextDecorationCollection());
        range.ApplyPropertyValue(TextElement.ForegroundProperty, editor.Foreground);
        range.ApplyPropertyValue(TextElement.BackgroundProperty, Brushes.Transparent);

        _fontColor = editor.Foreground;
        _highlight = Brushes.Transparent;
        UpdateSwatches();
        editor.Focus();
        RefreshState();
    }

    private void Undo_Click(object sender, RoutedEventArgs e)
    {
        if (Target is { CanUndo: true } editor)
        {
            editor.Undo();
            RefreshState();
        }
    }

    private void Redo_Click(object sender, RoutedEventArgs e)
    {
        if (Target is { CanRedo: true } editor)
        {
            editor.Redo();
            RefreshState();
        }
    }

    private void Cut_Click(object sender, RoutedEventArgs e)
    {
        Target?.Cut();
        RefreshState();
    }

    private void Copy_Click(object sender, RoutedEventArgs e)
    {
        Target?.Copy();
        RefreshState();
    }

    private void Paste_Click(object sender, RoutedEventArgs e)
    {
        if (Target is { } editor && ClipboardHasText())
        {
            editor.Paste();
            RefreshState();
        }
    }

    private void FontFamily_DropDownOpened(object sender, EventArgs e)
    {
        if (FontFamilyBox.ItemsSource is null)
        {
            FontFamilyBox.ItemsSource = SystemFontFamilyList.Value;
        }
    }

    private void FontFamily_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (_syncing || Target is null || FontFamilyBox.SelectedItem is not FontFamily family)
        {
            return;
        }

        ApplyProperty(TextElement.FontFamilyProperty, family);
        Target.Focus();
    }

    private void FontFamily_KeyDown(object sender, KeyEventArgs e)
    {
        if (e.Key == Key.Enter)
        {
            ApplyFontFamilyText();
            e.Handled = true;
        }
    }

    private void FontFamily_LostFocus(object sender, RoutedEventArgs e) => ApplyFontFamilyText();

    private void ApplyFontFamilyText()
    {
        var name = FontFamilyBox.Text?.Trim();
        if (_syncing || Target is null || string.IsNullOrEmpty(name))
        {
            return;
        }

        ApplyProperty(TextElement.FontFamilyProperty, new FontFamily(name));
        Target.Focus();
    }

    private void FontSize_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (_syncing || _syncingSize)
        {
            return;
        }

        ApplyFontSize(FontSizeBox.SelectedItem as string ?? FontSizeBox.Text);
    }

    private void FontSize_KeyDown(object sender, KeyEventArgs e)
    {
        if (e.Key == Key.Enter)
        {
            ApplyFontSize(FontSizeBox.Text);
            e.Handled = true;
        }
    }

    private void FontSize_LostFocus(object sender, RoutedEventArgs e) => ApplyFontSize(FontSizeBox.Text);

    private void ApplyFontSize(string? text)
    {
        if (_syncing || Target is null || string.IsNullOrWhiteSpace(text))
        {
            return;
        }

        if (!double.TryParse(text.Trim(), NumberStyles.Float, CultureInfo.CurrentCulture, out var size)
            || size < 1
            || size > 400)
        {
            return;
        }

        ApplyProperty(TextElement.FontSizeProperty, size);
        Target.Focus();
    }

    private void FontColorButton_Click(object sender, RoutedEventArgs e)
    {
        HighlightPopup.IsOpen = false;
        FontColorPopup.IsOpen = !FontColorPopup.IsOpen;
    }

    private void HighlightButton_Click(object sender, RoutedEventArgs e)
    {
        FontColorPopup.IsOpen = false;
        HighlightPopup.IsOpen = !HighlightPopup.IsOpen;
    }

    private void FontColor_Click(object sender, RoutedEventArgs e)
    {
        var editor = Target;
        if (editor is null)
        {
            return;
        }

        var brush = (sender as FrameworkElement)?.Tag as Brush ?? editor.Foreground;
        editor.Selection.ApplyPropertyValue(TextElement.ForegroundProperty, brush);
        _fontColor = brush;
        UpdateSwatches();
        FontColorPopup.IsOpen = false;
        editor.Focus();
        RefreshState();
    }

    private void Highlight_Click(object sender, RoutedEventArgs e)
    {
        var editor = Target;
        if (editor is null)
        {
            return;
        }

        var brush = (sender as FrameworkElement)?.Tag as Brush ?? Brushes.Transparent;
        editor.Selection.ApplyPropertyValue(TextElement.BackgroundProperty, brush);
        _highlight = brush;
        UpdateSwatches();
        HighlightPopup.IsOpen = false;
        editor.Focus();
        RefreshState();
    }
}
