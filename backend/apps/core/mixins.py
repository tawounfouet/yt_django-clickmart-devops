from rest_framework import serializers


class ValidateFieldsMixin:
    def validate(self, attrs):
        attrs = super().validate(attrs)
        unknown = set(self.initial_data.keys()) - set(self.fields.keys())
        if unknown:
            raise serializers.ValidationError({
                "non_field_errors":
                    f'Unknown field(s): {", ".join(sorted(unknown))}'
            })
        return attrs
