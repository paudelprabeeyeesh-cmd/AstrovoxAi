export interface PromptTemplate {
  name: string;
  version: string;
  description?: string;
  owner?: string;
  tags?: string[];
  inputs?: string[]; // required variable names
  content: string; // mustache-like template with {{var}} placeholders
  createdAt?: string;
  updatedAt?: string;
}

export interface PromptLibrary {
  templates: Record<string, PromptTemplate[]>; // name -> versions (sorted by semver or insertion)
}

export function validateTemplate(t: Partial<PromptTemplate>): { valid: boolean; errors: string[] } {
  const errors: string[] = [];
  if (!t.name || typeof t.name !== 'string') errors.push('name is required and must be string');
  if (!t.version || typeof t.version !== 'string') errors.push('version is required and must be string');
  if (!t.content || typeof t.content !== 'string') errors.push('content is required and must be string');
  if (t.inputs && !Array.isArray(t.inputs)) errors.push('inputs must be an array of strings');
  return { valid: errors.length === 0, errors };
}
