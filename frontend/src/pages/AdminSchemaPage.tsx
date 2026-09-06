import { useMutation, useQuery } from "@tanstack/react-query";
import { Fragment, useState } from "react";
import { useParams } from "react-router-dom";

import { api, type Permission } from "@/lib/api";

const roles = ["analyst", "viewer"] as const;

export function AdminSchemaPage() {
  const connectionId = Number(useParams().connectionId);
  const schema = useQuery({ queryKey: ["schema", connectionId], queryFn: () => api.schema(connectionId) });
  const [changes, setChanges] = useState<Record<string, boolean>>({});
  const [annotationChanges, setAnnotationChanges] = useState<Record<string, string>>({});
  const save = useMutation({
    mutationFn: (permissions: Permission[]) => api.updateSchema(connectionId, permissions),
  });
  const visible = (role: string, table: string, column: string | null) => {
    const key = `${role}:${table}:${column ?? "*"}`;
    if (key in changes) return changes[key];
    return schema.data?.permissions.find((item) => item.role === role && item.table_name === table && item.column_name === column)?.visible ?? true;
  };
  const toggle = (role: string, table: string, column: string | null) => {
    const key = `${role}:${table}:${column ?? "*"}`;
    setChanges({ ...changes, [key]: !visible(role, table, column) });
  };
  const submit = () => {
    const updates = Object.entries(changes).map(([key, value]) => {
      const [role, table_name, column] = key.split(":");
      return { role: role as "analyst" | "viewer", table_name, column_name: column === "*" ? null : column, visible: value };
    });
    save.mutate(updates);
    const annotations = Object.entries(annotationChanges).map(([key, description]) => {
      const [table_name, column] = key.split(":");
      return { table_name, column_name: column === "*" ? null : column, description };
    });
    if (annotations.length) void api.updateAnnotations(connectionId, annotations);
  };
  const annotation = (table: string, column: string | null, current: string) =>
    annotationChanges[`${table}:${column ?? "*"}`] ?? current;

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between"><h1 className="text-2xl font-semibold">Schema visibility</h1><button onClick={submit} className="rounded-md bg-primary px-4 py-2 text-primary-foreground">Save</button></div>
      <div className="overflow-auto rounded-md border">
        <table className="w-full text-sm"><thead className="bg-muted"><tr><th className="p-3 text-left">Table / column</th><th>Admin</th><th>Analyst</th><th>Viewer</th></tr></thead>
          <tbody>{schema.data?.tables.map((table) => (
            <Fragment key={table.name}><tr className="border-t font-medium"><td className="space-y-2 p-3"><span>{table.name}</span><input placeholder="Describe this table" value={annotation(table.name, null, table.description)} onChange={(event) => setAnnotationChanges({ ...annotationChanges, [`${table.name}:*`]: event.target.value })} className="block w-full rounded border px-2 py-1 text-xs font-normal" /></td><td className="text-center">✓</td>{roles.map((role) => <td key={role} className="text-center"><input type="checkbox" checked={visible(role, table.name, null)} onChange={() => toggle(role, table.name, null)} /></td>)}</tr>
              {table.columns.map((column) => <tr key={`${table.name}.${column.name}`} className="border-t text-muted-foreground"><td className="space-y-1 py-2 pl-8"><span>{column.name}</span><input placeholder="Business meaning" value={annotation(table.name, column.name, column.description)} onChange={(event) => setAnnotationChanges({ ...annotationChanges, [`${table.name}:${column.name}`]: event.target.value })} className="block w-full rounded border px-2 py-1 text-xs" /></td><td className="text-center">✓</td>{roles.map((role) => <td key={role} className="text-center"><input type="checkbox" checked={visible(role, table.name, column.name)} onChange={() => toggle(role, table.name, column.name)} /></td>)}</tr>)}
            </Fragment>
          ))}</tbody>
        </table>
      </div>
    </div>
  );
}
