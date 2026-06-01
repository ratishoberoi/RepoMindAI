export type FileTreeNode = {
  name: string;
  children: Record<string, FileTreeNode>;
  file?: boolean;
};

export function buildTree(files: Array<{ relative_path: string }>): FileTreeNode {
  const root: FileTreeNode = { name: "", children: {} };
  files.forEach((file) => {
    let node = root;
    file.relative_path.split("/").forEach((part, index, parts) => {
      node.children[part] = node.children[part] ?? { name: part, children: {} };
      node = node.children[part];
      if (index === parts.length - 1) node.file = true;
    });
  });
  return root;
}

export function shortName(value: string) {
  const clean = value.split("::")[0];
  const parts = clean.split("/");
  return parts.slice(-2).join("/");
}
