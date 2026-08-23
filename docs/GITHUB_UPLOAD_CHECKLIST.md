# Anonymous GitHub upload checklist

1. Create a new GitHub account or organization that does not expose an author
   name, institutional email, profile image, existing social graph, or personal
   commit history.
2. Create a new empty public repository. Do not fork an author-owned private
   repository because fork metadata can reveal identity.
3. Upload only the contents of this directory. Do not upload its parent
   workspace, manuscript build files, server command history, `.venv`, or old
   Git metadata.
4. Configure a neutral Git identity before the first commit, for example an
   anonymous display name and the platform-provided no-reply address.
5. Confirm that GitHub does not display a personal account as the repository
   owner, committer, package publisher, or workflow author.
6. Do not enable GitHub Actions for the anonymous-review version. The artifact
   intentionally has no one-click reproduction workflow, and hosted runner
   logs add avoidable metadata.
7. Compare uploaded files with `SHA256SUMS.txt`.
8. Run the individual checks in `REPRODUCTION_GUIDE.md` from a fresh clone,
   including the fixed-instance checker and one reference-encoder command.
9. Put the anonymous repository URL in the response letter and manuscript data
   availability statement.
10. After acceptance, either preserve the anonymous repository and archive it,
    or create a tagged archival mirror and replace the temporary link with its
    permanent DOI.

Before uploading, repeat a text scan for local identifiers such as machine
usernames, IP addresses, drive-letter paths, home-directory paths, author
emails, and affiliations.
