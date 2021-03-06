import datetime

from django.utils import timezone
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User, Group, AnonymousUser
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework import status
from rest_framework import authentication
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.views import APIView

from backend import serializers
from backend.permissions import IsOwnerOrReadOnly
from backend.authentication import CsrfExemptSessionAuthentication
from backend.models import Tag, Portal, Comment, TagType


EXPIRE_MINUTES = getattr(settings, 'REST_FRAMEWORK_TOKEN_EXPIRE_MINUTES', 1)


class DefaultMixin(object):
    authentication_classes = (
        authentication.SessionAuthentication,
        authentication.BasicAuthentication,
        authentication.TokenAuthentication
    )

    permission_classes = (
        permissions.IsAuthenticated,
    )
    pagination_by = 25
    pagination_by_param = 'page_size'
    max_pagination_by = 100


class IsOwnerOrReadOnlyMixin(DefaultMixin):
    permission_classes = (
        permissions.IsAuthenticatedOrReadOnly,
        IsOwnerOrReadOnly
    )


class ObtainExpiringAuthToken(ObtainAuthToken):
    """
    Post：
    提交用户账号密码，获取用户Token。
    """

    @csrf_exempt
    def post(self, request, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            token, created = Token.objects.get_or_create(user=serializer.validated_data['user'])

            time_now = timezone.now()

            if created or token.created < (time_now - datetime.timedelta(minutes=EXPIRE_MINUTES)):
                # Update the created time of the token to keep it valid
                token.delete()
                token = Token.objects.create(user=serializer.validated_data['user'])
                token.created = time_now
                token.save()

            return Response({'token': token.key})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserViewSet(DefaultMixin, viewsets.ReadOnlyModelViewSet):
    """
    list:
    获取用户列表  query: 携带`?query=myself`时查询自己信息
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = serializers.UserSerializer

    def list(self, request, *args, **kwargs):
        if request.query_params.get('query') == 'myself':  # 查询自己
            user = get_object_or_404(User.objects.all(), pk=request.user.id)
            serializer = serializers.UserSerializer(user)
            serializer.context['request'] = request  # 生成超链接需要
            return Response(serializer.data)
        return super(UserViewSet, self).list(request, args, kwargs)

    # def retrieve(self, request, pk=None, *args, **kwargs):
    #     queryset = User.objects.all()
    #     user = get_object_or_404(queryset, pk=pk)
    #     serializer = serializers.UserSerializer(user)
    #     serializer.context['request'] = request
    #     return Response(serializer.data)


class GroupViewSet(DefaultMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Group.objects.all()
    serializer_class = serializers.GroupSerializer


class TagTypeViewSet(DefaultMixin, viewsets.ModelViewSet):
    queryset = TagType.objects.all()
    serializer_class = serializers.TagTypeSerializer


class PortalViewSet(DefaultMixin, viewsets.ModelViewSet):
    queryset = Portal.objects.all()
    serializer_class = serializers.PortalSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class TagViewSet(DefaultMixin, viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = serializers.TagSerializer


class CommentViewSet(DefaultMixin, viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = serializers.CommentSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class IITCView(APIView):
    authentication_classes = (
        authentication.BasicAuthentication,
        authentication.TokenAuthentication,
    )
    # def get(self, request, *args, **kwargs):
    #     print(self.request.user)
    #     return Response({})

    def post(self, request, *args, **kwargs):
        def check_data(portal):
            guid = portal['guid']
            data = portal['data']
            # 保留小数点后六位的坐标
            latE6 = data['latE6']/1000000
            lngE6 = data['lngE6']/1000000
            image = data['image']
            title = data['title']
            timestamp = data['timestamp']
            print(guid, latE6, lngE6, image, title, timestamp)
            url = 'https://ingress.com/intel?ll=%s,%s&z=17&pll=%s,%s' % (latE6, lngE6, latE6, lngE6)
            guid_po = Portal.objects.filter(guid=guid).first()
            link_po = Portal.objects.filter(link=url).first()
            if not guid_po and not link_po:
                Portal.objects.create(guid=guid, late6=latE6, lnge6=lngE6,
                                      image=image, title=title, timestamp=timestamp,
                                      link=url, author=self.request.user)
            elif link_po or guid_po:
                old_po = link_po or guid_po
                old_po.link = url
                old_po.guid = guid
                old_po.late6 = latE6
                old_po.lnge6 = lngE6
                old_po.image = image
                old_po.title = title
                old_po.timestamp = timestamp
                old_po.save()
        if isinstance(self.request.user, AnonymousUser):
            response = Response({'detail': '你谁啊？'})
            response.status_code = 401
            return response

        try:
            if request.query_params.get('type') == 'single':  # 单个据点上传
                # print(self.request.user)
                # print(self.request.data)
                check_data(self.request.data)
                response = Response({'detail': 'ok'})
                response.status_code = 201

            elif request.query_params.get('type') == 'many':
                for po in self.request.data:
                    check_data(po)
                response = Response({'detail': 'ok'})
                response.status_code = 201
            else:
                response = Response({'detail': '你瞅啥？'})
                response.status_code = 400
        except KeyError:
            response = Response({'detail': '请通过tg/GitHub联系@bllli'})
            response.status_code = 400
        return response
