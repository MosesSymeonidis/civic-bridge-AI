export type DashboardSeverity =
  | 'ordinary-political-expression'
  | 'offensive-or-harmful-expression'
  | 'potential-hate-speech'
  | 'high-severity-incitement-risk'

export type DashboardParticipantType =
  | 'student'
  | 'educator'
  | 'social-media'

export const dashboardSeverityOptions: Array<{
  value: DashboardSeverity
  label: string
}> = [
  {
    value: 'ordinary-political-expression',
    label: 'Ordinary political expression',
  },
  {
    value: 'offensive-or-harmful-expression',
    label: 'Offensive or harmful expression',
  },
  {
    value: 'potential-hate-speech',
    label: 'Potential hate speech',
  },
  {
    value: 'high-severity-incitement-risk',
    label: 'High-severity incitement risk',
  },
]

export type DashboardIncidentProfile = {
  country: string
  regionArea: string
  language: string
}

export function buildIncidentProfileDashboardUrl(
  profile: DashboardIncidentProfile,
): string {
  const url = new URL('/public-institutions', window.location.origin)

  url.searchParams.set('time_range', '30d')
  url.searchParams.set('minimum_group_size', '1')
  url.searchParams.set('open_selections', 'true')

  if (profile.country) {
    url.searchParams.set('country', profile.country)
  }
  if (profile.regionArea) {
    url.searchParams.set('region_area', profile.regionArea)
  }
  if (profile.language) {
    url.searchParams.set('language', profile.language)
  }
  return url.toString()
}
