'''
사전에 VPC 및 구성 요소들이 미리 생성되어 있다는 것을 가정하고 실행

실행 순서 및 api function
create_flow_logs(**kwargs)
1. Client 정보 요구 (액세스키/리전/VPC)
    - VPC는 리전까지 선택 후 받아와서 선택하도록 하기
2. Amazon S3 버킷 생성
3. VPC Flow Logs 생성 및 Amazon S3 연결
    - 로그 축적 주기 1분으로 설정하고 총 6분간 축적
    - 2분마다 버킷으로부터 VPC Flow Log 가져와 데이터 정제 (데이터 시퀀싱 고민 필요)
    - 6분 이후 생성한 VPC Flow Logs 및 S3 버킷 삭제
4. 축적한 데이터를 이용해 D3.js를 이용한 네트워크 토폴로지 작성 (선택한 VPC-
    - force-direct-graph 예제 사용 (https://observablehq.com/@d3/mobile-patent-suits?collection=@d3/d3-force)
5. 작성한 데이터 csv 형식으로 변환해 python DF 형태로 저장
6. 4번과 5번의 결과물을 gui 형태로 표현

각 단계별 aws api function (Core 기능 : 2단계, 3단계, 5단계 DF 생성)
1단계
- 
2단계
- create_bucket(**kwargs)
3단계
- create_flow_logs(**kwargs)
4단계


'''
import boto3
import logging
from copy import deepcopy
import pandas as pd
from glob import glob
from botocore.exceptions import ClientError
# from pprint import pprint


Access_Key = ""
Secret_Key = ""
Region = None
VPC = None
Region_List = {"미국 동부 (버지니아 북부)":"us-east-1","미국 동부 (오하이오)":"us-east-2","미국 서부 (캘리포니아)":"us-west-1","미국 서부 (오레곤)":"us-west-2","아프리카 (케이프타운)":"af-south-1","아시아 태평양 (홍콩)":"ap-east-1","아시아 태평양 (뭄바이)":"ap-south-1","아시아 태평양 (오사카)":"ap-northeast-3","아시아 태평양 (서울)":"ap-northeast-2","아시아 태평양 (싱가포르)":"ap-southeast-1","아시아 태평양 (시드니)":"ap-southeast-2","아시아 태평양 (도쿄)":"ap-northeast-1","캐나다 (중부)":"ca-central-1","유럽 (프랑크푸르트)":"eu-central-1","유럽 (아일랜드)":"eu-west-1","유럽 (런던)":"eu-west-2","유럽 (밀라노)":"eu-south-1","유럽 (파리)":"eu-west-3","유럽 (스톡홀름)":"eu-north-1","중동 (바레인)":"me-south-1","남아메리카 (상파울루)":"sa-east-1"}
S3_client = None
VPC_client = None

def Read_Credential():
    """
    Read Credential File from Directory
    Caution : "ONLY ONE" Credential CSV file should be in the directory
    """
    global Access_Key
    global Secret_Key
    global Region
    global S3_client
    global VPC_client
    
    data = None
    
    for f in glob('*.csv'):
        data = pd.read_csv(f).values
    
    if data != None:
        Access_Key = data[0][0]
        Secret_Key = data[0][1]
        S3_client = boto3.client('s3', aws_access_key_id=Access_Key, aws_secret_access_key=Secret_Key,region_name=Region)
        VPC_client = boto3.client('ec2', aws_access_key_id=Access_Key, aws_secret_access_key=Secret_Key,region_name=Region)
        print("자격증명 파일 확인 완료, 액세스 키 : {}\n".format(Access_Key))
    else:
        S3_client = boto3.client('s3', region_name=Region)
        VPC_client = boto3.client('ec2', region_name=Region)
        print("AWS CLI를 통해 자격증명 확인 완료\n")
    
def Selector(object_list:dict, object:str, resource:str):
    """
    Select Module
    object_list is dictionary {name_tag : read_id} form
    """
    i = 1
    for k,v in object_list.items():
        print(i, ". "+k)
        i += 1
    iter = int(input(resource + "을(를) 선택하세요 : "))
    
    object = list(object_list.values())[iter - 1]
    print("선택 {} : {}\n".format(resource, object))
    return object
    
def Get_VPC_info():
    global VPC_client
    vpc_name_list = list()
    vpc_id_list = list()
    
    try:
        result = VPC_client.describe_vpcs()
        for i in range(len(result['Vpcs'])):
            vpc_name_list.append(result['Vpcs'][i]['Tags'][0]['Value'])
            vpc_id_list.append(result['Vpcs'][i]['VpcId'])
        vpcs = dict(zip(vpc_name_list,vpc_id_list))      
    except ClientError as e:
        logging.error(e)
        return False
    return vpcs
    
def Create_bucket(region=Region):
    """
    Create an S3 bucket in a selected region
    This S3 bucket will be deleted after VPC Flow Log information
    """
    global S3_client
    
    try:
        location = {'LocationConstraint': region}
        S3_client.create_bucket(Bucket="py-flowlog-temp", CreateBucketConfiguration=location)
        print("VPC Flow Log 저장 버킷 생성 완료, 버킷 이름 : \"py-flowlog-temp\"\n")
    except ClientError as e:
        logging.error(e)
        return False
    return True

def Create_log(vpc, region=Region):
    """
    Create VPC Flow Log and stack logs in S3 bucket
    """
    global VPC_client
    try:
        VPC_client.create_flow_logs(ResourceType='VPC',TrafficType='ALL',LogDestinationType='s3',LogDestination='arn:aws:s3:::py-flowlog-temp',LogFormat='${version} ${account-id} ${interface-id} ${srcaddr} ${dstaddr} ${srcport} ${dstport} ${protocol} ${packets} ${bytes} ${start} ${end} ${action} ${log-status}',ReasourceIds=[vpc])
    except ClientError as e:
        logging.error(e)
        return False
    return True
    
# def Test_func(region=Region):
    # global S3_client
    # try:
        # tempData = S3_client.get_bucket_inventory_configuration()
        # print(tempData)
    # except ClientError as e:
        # logging.error(e)
        # return False
    # return True    
    
####################################################################################################

# Main Process 

# Identify Credential & Get Information
Region = Selector(Region_List, Region, "Region")
Read_Credential()
VPC = Selector(Get_VPC_info(), VPC, "VPC")

# Start Main Process
Create_bucket(Region)
Create_log(Region)


# Test Phase


