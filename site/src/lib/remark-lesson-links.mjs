// Rewrites links written for GitHub into links that work on the site:
//   "01-whose-data-is-this.md"         -> "/course/01-whose-data-is-this/"
//   "01-whose-data-is-this.md#heading" -> "/course/01-whose-data-is-this/#heading"
//   "../../docs/adr/0001-x.md"         -> the same file on GitHub
// The repo is private for now, so the GitHub links only work for its owner.
const REPO_BLOB = "https://github.com/mayowabodunwa/deskly-saas-lab/blob/main/";

function rewrite(url) {
  const lesson = url.match(/^(?:\.\/)?(\d\d-[\w-]+)\.mdx?(#.*)?$/);
  if (lesson) return `/course/${lesson[1]}/${lesson[2] ?? ""}`;
  if (url.startsWith("../../")) return REPO_BLOB + url.slice("../../".length);
  return url;
}

function walk(node) {
  if (node.type === "link" && typeof node.url === "string") node.url = rewrite(node.url);
  for (const child of node.children ?? []) walk(child);
}

export function remarkLessonLinks() {
  return (tree) => walk(tree);
}
