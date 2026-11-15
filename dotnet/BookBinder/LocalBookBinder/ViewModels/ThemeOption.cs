using System.ComponentModel;
using System.Runtime.CompilerServices;
using System.Windows.Input;
using System.Windows.Media;
using LocalBookBinder.Infrastructure;

namespace LocalBookBinder.ViewModels;

public sealed class ThemeOption : INotifyPropertyChanged
{
    private bool _isActive;

    public ThemeOption(ThemeDefinition definition, Action<ThemeOption> select)
    {
        Definition = definition;
        SelectCommand = new RelayCommand(() => select(this));
    }

    public ThemeDefinition Definition { get; }
    public string Id => Definition.Id;
    public string DisplayName => Definition.DisplayName;
    public string Kind => Definition.IsDark ? "Dark" : "Light";
    public Brush PreviewBackground => Definition.PreviewBackground;
    public Brush PreviewAccent => Definition.PreviewAccent;
    public Brush PreviewForeground => Definition.PreviewForeground;
    public ICommand SelectCommand { get; }

    public bool IsActive
    {
        get => _isActive;
        set
        {
            if (_isActive == value) return;
            _isActive = value;
            OnPropertyChanged();
        }
    }

    public event PropertyChangedEventHandler? PropertyChanged;

    private void OnPropertyChanged([CallerMemberName] string? name = null)
        => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
}