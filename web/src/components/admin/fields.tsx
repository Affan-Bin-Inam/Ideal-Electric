type Common = {
  name: string;
  label: string;
  hint?: string;
  error?: string;
  required?: boolean;
  wide?: boolean; // spans both columns
};

const inputClass = "mt-1 w-full rounded border border-ink/20 bg-white px-3 py-2 text-sm";

function describedBy(c: Common) {
  return (
    [c.hint ? `${c.name}-hint` : "", c.error ? `${c.name}-error` : ""].filter(Boolean).join(" ") ||
    undefined
  );
}

function Wrap(props: Common & { children: React.ReactNode }) {
  return (
    <div className={props.wide ? "sm:col-span-2" : undefined}>
      <label htmlFor={props.name} className="text-sm font-semibold">
        {props.label}
        {props.required && <span aria-hidden> *</span>}
      </label>
      {props.children}
      {props.hint && (
        <p id={`${props.name}-hint`} className="mt-1 text-xs text-muted">
          {props.hint}
        </p>
      )}
      {props.error && (
        <p id={`${props.name}-error`} className="mt-1 text-sm text-action">
          {props.error}
        </p>
      )}
    </div>
  );
}

export function TextField(
  props: Common & {
    defaultValue: string | null;
    type?: "text" | "email" | "url" | "tel";
  },
) {
  const { defaultValue, type = "text", ...common } = props;
  return (
    <Wrap {...common}>
      <input
        id={common.name}
        name={common.name}
        type={type}
        defaultValue={defaultValue ?? ""}
        required={common.required}
        aria-invalid={common.error ? true : undefined}
        aria-describedby={describedBy(common)}
        className={inputClass}
      />
    </Wrap>
  );
}

export function TextArea(props: Common & { defaultValue: string | null; rows?: number }) {
  const { defaultValue, rows = 3, ...common } = props;
  return (
    <Wrap {...common}>
      <textarea
        id={common.name}
        name={common.name}
        rows={rows}
        defaultValue={defaultValue ?? ""}
        required={common.required}
        aria-invalid={common.error ? true : undefined}
        aria-describedby={describedBy(common)}
        className={inputClass}
      />
    </Wrap>
  );
}

export function CheckField(props: {
  name: string;
  label: string;
  hint?: string;
  defaultChecked: boolean;
}) {
  return (
    <div className="sm:col-span-2">
      <label className="flex items-center gap-2 text-sm font-semibold">
        <input type="checkbox" name={props.name} defaultChecked={props.defaultChecked} />
        {props.label}
      </label>
      {props.hint && <p className="mt-1 text-xs text-muted">{props.hint}</p>}
    </div>
  );
}

export function FormSection(props: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-lg bg-white p-6 shadow-sm">
      <h2 className="text-lg font-bold tracking-tight">{props.title}</h2>
      {props.description && <p className="mt-1 text-sm text-muted">{props.description}</p>}
      <div className="mt-4 grid gap-4 sm:grid-cols-2">{props.children}</div>
    </section>
  );
}