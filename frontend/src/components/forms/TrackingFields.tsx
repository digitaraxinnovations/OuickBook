"use client";

import { Field, Select } from "@/components/ui/FormFields";
import { useLoad } from "@/hooks/useLoad";
import { trackingService } from "@/services";
import { TrackingInput } from "@/types/inputs";

export function emptyTracking(): TrackingInput {
  return { class_id: null, location_id: null, project_id: null, tag_ids: [] };
}

interface TrackingFieldsProps {
  value: TrackingInput;
  onChange: (value: TrackingInput) => void;
  /** Sales forms: only this customer's projects can be picked. */
  customerId?: number | null;
  /** Manual journal entries put class/location/project on each line, so only tags are shown here. */
  tagsOnly?: boolean;
}

/**
 * Class, location, project and tags of a transaction. Each field only shows
 * once the company has set up at least one (Accounting -> Classes, locations & tags).
 */
export function TrackingFields({ value, onChange, customerId, tagsOnly = false }: TrackingFieldsProps) {
  const classes = useLoad(() => trackingService.list("classes"));
  const locations = useLoad(() => trackingService.list("locations"));
  const projects = useLoad(() => trackingService.projects(true));
  const tags = useLoad(() => trackingService.tags());

  const classOptions = (classes.data || []).filter((item) => item.is_active).map((item) => ({ value: item.id, label: item.name }));
  const locationOptions = (locations.data || []).filter((item) => item.is_active).map((item) => ({ value: item.id, label: item.name }));
  const projectOptions = (projects.data || [])
    .filter((project) => !customerId || project.customer_id === customerId)
    .map((project) => ({ value: project.id, label: project.name }));
  const allTags = tags.data || [];
  const chosenTags = value.tag_ids || [];

  function toggleTag(tagId: number) {
    if (chosenTags.includes(tagId)) {
      onChange({ ...value, tag_ids: chosenTags.filter((id) => id !== tagId) });
    } else {
      onChange({ ...value, tag_ids: [...chosenTags, tagId] });
    }
  }

  function numberOrNull(text: string): number | null {
    return text ? Number(text) : null;
  }

  const showClass = !tagsOnly && classOptions.length > 0;
  const showLocation = !tagsOnly && locationOptions.length > 0;
  const showProject = !tagsOnly && projectOptions.length > 0;
  if (!showClass && !showLocation && !showProject && allTags.length === 0) {
    return null;
  }

  return (
    <div className="grid gap-4 md:grid-cols-4">
      {showClass && (
        <Field label="Class">
          <Select value={value.class_id ?? ""} onChange={(e) => onChange({ ...value, class_id: numberOrNull(e.target.value) })} placeholder="None" options={classOptions} />
        </Field>
      )}
      {showLocation && (
        <Field label="Location">
          <Select value={value.location_id ?? ""} onChange={(e) => onChange({ ...value, location_id: numberOrNull(e.target.value) })} placeholder="None" options={locationOptions} />
        </Field>
      )}
      {showProject && (
        <Field label="Project">
          <Select value={value.project_id ?? ""} onChange={(e) => onChange({ ...value, project_id: numberOrNull(e.target.value) })} placeholder="None" options={projectOptions} />
        </Field>
      )}
      {allTags.length > 0 && (
        <div className={showClass || showLocation || showProject ? "" : "md:col-span-4"}>
          <div className="mb-1 text-sm font-medium text-gray-700">Tags</div>
          <div className="flex flex-wrap gap-1">
            {allTags.map((tag) => {
              const chosen = chosenTags.includes(tag.id);
              return (
                <button
                  key={tag.id}
                  type="button"
                  onClick={() => toggleTag(tag.id)}
                  className={"rounded-full border px-2 py-0.5 text-xs " + (chosen ? "border-brand-600 bg-brand-50 text-brand-700" : "border-gray-300 text-gray-600")}
                  title={tag.group_name || undefined}
                >
                  {tag.name}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
