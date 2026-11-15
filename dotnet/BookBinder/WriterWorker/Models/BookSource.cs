namespace WriterWorker.Models
{
    /// <summary>
    /// Tree a book was read from. The pages show it next to the title so a reader can tell a
    /// working copy from a finished edition.
    /// </summary>
    public enum BookSource
    {
        /// <summary>A book of the writer pipeline, for example <c>workspaces\pipeline\nouka</c>.</summary>
        Pipeline,

        /// <summary>A book that only exists as a plan, for example <c>templates\backlog\v1</c>.</summary>
        Backlog,

        /// <summary>A finished edition, for example <c>workspaces\published\nouka\version6</c>.</summary>
        Published,
    }
}
