{{- define "task-tracker.name" -}}{{ .Chart.Name }}{{- end }}

{{- define "task-tracker.fullname" -}}
{{- if contains .Chart.Name .Release.Name -}}{{ .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else -}}{{ printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" }}{{- end -}}
{{- end }}

{{- define "task-tracker.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
app.kubernetes.io/name: {{ include "task-tracker.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: devops-task-tracker
{{- end }}

{{- define "task-tracker.selectorLabels" -}}
app.kubernetes.io/name: {{ include "task-tracker.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "task-tracker.secretName" -}}
{{- if .Values.secret.existingSecret -}}{{ .Values.secret.existingSecret }}
{{- else -}}{{ include "task-tracker.fullname" . }}-secret{{- end -}}
{{- end }}

{{- define "task-tracker.claimName" -}}
{{- if .Values.persistence.existingClaim -}}{{ .Values.persistence.existingClaim }}
{{- else -}}{{ include "task-tracker.fullname" . }}-data{{- end -}}
{{- end }}
