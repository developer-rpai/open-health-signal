export type SelectedWorkItem = {
  title: string;
  venue: string;
  year: number;
  url: string;
};

/** Papers shown on About. The section stays hidden while this list is empty. */
export const SELECTED_WORK: SelectedWorkItem[] = [];
