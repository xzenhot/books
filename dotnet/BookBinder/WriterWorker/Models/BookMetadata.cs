using System;

namespace WriterWorker.Models;

/// <summary>Binding of a printed book: the cheap paperback or the stiff hard cover.</summary>
public enum BookCoverType
{
    Paperback,
    HardCover
}

/// <summary>
/// The publishing details of a book - the name it is displayed under, who wrote and composed it,
/// the publisher, the price of each binding, the ISBN and the copyright line. They describe the
/// book rather than the way it prints, so they are kept in the <c>book</c> object of the
/// <c>profile.json</c> of the book folder, next to the paper, the font and the page folders it
/// prints with, and are asked for in the Book Model tab of the PDF setup.
/// </summary>
public class BookMetadata
{
    /// <summary>Unique name the book is displayed under in the library and on the cover.</summary>
    public string? DisplayName { get; set; }

    /// <summary>Name of the author printed on the cover and the title page.</summary>
    public string? Author { get; set; }

    /// <summary>Short biography printed on the back cover or the about page.</summary>
    public string? AboutAuthor { get; set; }

    /// <summary>Description of the book printed on the back cover or the about page.</summary>
    public string? AboutBook { get; set; }

    /// <summary>Binding the book is sold in.</summary>
    public BookCoverType CoverType { get; set; } = BookCoverType.Paperback;

    /// <summary>Price of the paperback edition; null when the edition is not sold on its own.</summary>
    public decimal? PaperbackPrice { get; set; }

    /// <summary>Price of the hard cover edition; null when the edition is not sold on its own.</summary>
    public decimal? HardCoverPrice { get; set; }

    /// <summary>ISBN of the edition, as printed above the barcode.</summary>
    public string? Isbn { get; set; }

    public string? PublisherName { get; set; }

    public string? PublisherAddress { get; set; }

    /// <summary>Image of the publisher's logo printed on the cover and the title page.</summary>
    public string? PublisherLogoPath { get; set; }

    /// <summary>Name of the composer of the music the book is set to, when it is.</summary>
    public string? Composer { get; set; }

    /// <summary>Name of the artist who painted the cover.</summary>
    public string? CoverArtist { get; set; }

    /// <summary>Year the edition was produced.</summary>
    public int? YearOfProduction { get; set; }

    /// <summary>Copyright line of the edition, for example "(c) 2026 Pijush Kanti".</summary>
    public string? Copyright { get; set; }

    /// <summary>A deep copy, so a caller can edit the details without touching the original.</summary>
    public virtual BookMetadata Clone() => (BookMetadata)MemberwiseClone();

    /// <summary>Copies the details of <paramref name="source"/> onto this instance.</summary>
    public void CopyFrom(BookMetadata? source)
    {
        if (source is null)
        {
            return;
        }

        DisplayName = source.DisplayName;
        Author = source.Author;
        AboutAuthor = source.AboutAuthor;
        AboutBook = source.AboutBook;
        CoverType = source.CoverType;
        PaperbackPrice = source.PaperbackPrice;
        HardCoverPrice = source.HardCoverPrice;
        Isbn = source.Isbn;
        PublisherName = source.PublisherName;
        PublisherAddress = source.PublisherAddress;
        PublisherLogoPath = source.PublisherLogoPath;
        Composer = source.Composer;
        CoverArtist = source.CoverArtist;
        YearOfProduction = source.YearOfProduction;
        Copyright = source.Copyright;
    }

    /// <summary>Fills in what a hand-edited or older file may leave out.</summary>
    public BookMetadata Normalize()
    {
        DisplayName = Trim(DisplayName);
        Author = Trim(Author);
        AboutAuthor = Trim(AboutAuthor);
        AboutBook = Trim(AboutBook);
        Isbn = Trim(Isbn);
        PublisherName = Trim(PublisherName);
        PublisherAddress = Trim(PublisherAddress);
        PublisherLogoPath = Trim(PublisherLogoPath);
        Composer = Trim(Composer);
        CoverArtist = Trim(CoverArtist);
        Copyright = Trim(Copyright);

        if (!Enum.IsDefined(CoverType))
        {
            CoverType = BookCoverType.Paperback;
        }

        if (PaperbackPrice is < 0)
        {
            PaperbackPrice = null;
        }

        if (HardCoverPrice is < 0)
        {
            HardCoverPrice = null;
        }

        if (YearOfProduction is < 1 or > 9999)
        {
            YearOfProduction = null;
        }

        return this;
    }

    private static string? Trim(string? text)
    {
        var trimmed = text?.Trim();
        return string.IsNullOrEmpty(trimmed) ? null : trimmed;
    }

    public override string ToString() => DisplayName ?? Author ?? string.Empty;
}
