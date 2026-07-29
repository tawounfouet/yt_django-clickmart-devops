from rest_framework import viewsets, status
from rest_framework.response import Response
from images.models import Image
from images.api.serializers import ImageSerializer


class ImageViewSet(viewsets.ModelViewSet):
    queryset = Image.objects.all()
    serializer_class = ImageSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        image = serializer.save(original_filename=request.data['file'].name)
        return Response(
            ImageSerializer(image).data,
            status=status.HTTP_201_CREATED,
        )
