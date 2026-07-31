from rest_framework import serializers


class ValidateFieldsMixin:
    def validate(self, attrs):
        attrs = super().validate(attrs)
        unknown = set(self.initial_data.keys()) - set(self.fields.keys())
        if unknown:
            raise serializers.ValidationError({
                serializers.NON_FIELD_ERRORS_KEY:
                    f'Unknown field(s): {", ".join(sorted(unknown))}'
            })
        return attrs
