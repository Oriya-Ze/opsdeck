{{- define "opsdeck.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "opsdeck.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{- define "opsdeck.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "opsdeck.labels" -}}
helm.sh/chart: {{ include "opsdeck.chart" . }}
{{ include "opsdeck.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "opsdeck.selectorLabels" -}}
app.kubernetes.io/name: {{ include "opsdeck.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "opsdeck.backend.fullname" -}}
{{- printf "%s-backend" (include "opsdeck.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "opsdeck.frontend.fullname" -}}
{{- printf "%s-frontend" (include "opsdeck.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "opsdeck.postgresql.fullname" -}}
{{- printf "%s-postgresql" (include "opsdeck.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "opsdeck.backend.selectorLabels" -}}
{{ include "opsdeck.selectorLabels" . }}
app.kubernetes.io/component: backend
{{- end }}

{{- define "opsdeck.frontend.selectorLabels" -}}
{{ include "opsdeck.selectorLabels" . }}
app.kubernetes.io/component: frontend
{{- end }}

{{- define "opsdeck.postgresql.selectorLabels" -}}
{{ include "opsdeck.selectorLabels" . }}
app.kubernetes.io/component: postgresql
{{- end }}

{{- define "opsdeck.databaseUrl" -}}
{{- if .Values.secrets.databaseUrl }}
{{- .Values.secrets.databaseUrl }}
{{- else if .Values.postgresql.enabled }}
{{- printf "postgresql://%s:%s@%s:%d/%s" .Values.postgresql.auth.username .Values.postgresql.auth.password (include "opsdeck.postgresql.fullname" .) (.Values.postgresql.service.port | int) .Values.postgresql.auth.database }}
{{- else }}
{{- fail "DATABASE_URL required: enable postgresql, set secrets.databaseUrl, or set secrets.existingSecret" }}
{{- end }}
{{- end }}
