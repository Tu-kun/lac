import difflib
import os
import re
import sys
import time
from LAC import LAC


def timmer(func):
    def wrapper(*args, **kwargs):
        print('\n函数：{_funcname_}() 开始运行：'.format(_funcname_=func.__name__))
        start_time = time.time()
        res = func(*args, **kwargs)
        end_time = time.time()
        print('函数: {_funcname_}()运行了 {_time_}秒'
              .format(_funcname_=func.__name__, _time_=(end_time - start_time)))
        return res

    return wrapper


class pic_classify:

    def __init__(self, listDirs, result_path):
        # 添加自定义词典
        self.load_dic()
        self.listDirs = listDirs
        self.result_path = result_path
        self.last_title = ''  # 存放上一次的图片标题
        self.last_result = []  # 存放上一次的处理结果
        self.last_number = ''  # 存放上一次的处理结果,每次编号都不一样

    def load_dic(self):
        """
        将jieba词典的数据加载进来，构成自己的词典
        :return:
        """
        # 添加自定义词典
        Path = os.path.dirname(os.getcwd())
        ciku_Path = Path + os.sep + "词库" + os.sep

        self.places = self.load_Userdict(ciku_Path + '中国风景名胜.txt')
        self.countries = self.load_Userdict(ciku_Path + '国家和地区词库.txt')
        self.stop_words = self.load_Userdict(ciku_Path + 'stop-words.txt')
        self.names = self.load_Userdict(ciku_Path + 'names.txt')

    def load_Userdict(self, path):
        """
        加载自定义词典,字典格式为  “关键字 词性”中间用一个空格隔开
        :param path:
        :return:返回字典格式的信息
        """
        with open(path, 'r', encoding='utf-8') as f:
            user_dic = f.read().splitlines()
            dic = {}
            for i in user_dic:
                line = i.split(' ')
                dic[line[0]] = line[1]
        return dic

    def get_time(self, title):
        """
        获取图片的拍摄时间
        :param title: 图片标题
        :return: 返回year,month,day
        """
        print('开始进行时间提取：{}'.format(title))
        year, month, day = None, None, None

        pattern = re.compile(r'(20\d{2}-\d{1,2}-\d{1,2})'  # 匹配 2020-4-5 和 2020-04-05 格式
                             r'|(20\d{2}年\d{1,2}月\d{1,2}'  # 匹配 2016年11月18日格式
                             r'|(20\d{2}(([0][0-9])|([1][0-2]))\d{1,2})'  # 匹配2016021 或 2016102 20161102格式
                             r'|(20\d{2}—\d{1,2}—\d{1,2}))', re.X)  # 匹配 2020—01—10 格式，此处连接符为中文破折号的一半
        try:
            time = re.search(pattern, title).group()
            print('时间：{}'.format(time))
            year = re.search(r'20\d{2}', time).group()  # 提取年份，以20开头
            month = re.search(r'\d{1,2}', time[4:]).group()  # 提取月份
            day = re.search(r'\d{1,2}', time[-2:]).group()  # 提取日期
        except Exception:
            pass

        # 此处处理只有年份的数据，只有年份时上面的匹配规则是无法生效的
        if year is None:
            try:
                year = re.search(r'20\d{2}', title).group()  # 匹配20开头的4位数的年份
            except Exception:
                pass

        # 考虑日期格式读取错误导致月份大于12（通常为连续读取两个年份如20102012），同时统计月份为空的数据
        if month is None or int(month) > 12:
            month, day = self.get_monthAndDay(title)

        time = year, month, day
        return time

    def get_monthAndDay(self, title):
        """
        第一轮读取时间失败后调用，在年份和日期中存在间隔时调用，如2012年xxxx，4月12日，5.15,只有月份信息的情况
        :param title: 照片标题字符串
        :return: month, day 返回月份和日期
        """
        month, day = None, None
        # print("二次时间读取:{}".format(title))
        try:
            time = re.search(r'\d{1,2}月\d{1,2}', title).group()
            month = re.search(r'\d{1,2}', time).group()
            day = re.search(r'\d{1,2}', time[2:]).group()
            # print('二次读取月份和日期；{}  {}'.format(month, day))
        except Exception:
            pass
        try:
            print('*' * 100)
            time = re.search(r'\d{1,2}\\\d{1,2}', r'' + title).group()
            # print('此处time为：{}'.format(time))
            day = re.match(r'^\d{1,2}', time).group()
            month = re.search(r'\d{1,2}', time[2:]).group()
        except Exception:
            print("时间读取失败")
        try:
            time = re.search(r'\d{1,2}月', title).group()
            month = re.search(r'\d{1,2}', time).group()
        except Exception:
            print("时间读取失败")

        # Z:\yuexun\2017年外拍\闫珅\文博会911—JPG\闫珅—文博会911—JPG (973).jpg --> 00012159.jpg  这个日期无法提取，在此处手动添加
        if '文博会' in title:
            month = 9
            day = 11

        return month, day

    # @timmer
    def get_keyWords_byseg(self, title, seg):
        '''
        通过分词并比对已存在的语料库来获取摄影师姓名、国籍和拍摄地点和关键词
        :param title: 图片标题1
        :param seg: seg
        :return: loc, final_kew_words, names, nationality 拍摄地，关键词，摄影师名，摄影师国籍
        '''
        print("开始对信息进行处理:{}".format(title))

        keywords_list = [i for i in seg.run(title) if i != ' ']  # 进行分词，并去除空值
        names = list(set([i for i in keywords_list if i in self.names.keys()]))  # 若摄影师名字已存在与给定的文件中,同时进行去重处理
        nationality = list(set([i for i in keywords_list if i in self.countries.keys()]))  # 摄影师国籍
        loc = list(set([i for i in keywords_list if i in self.places.keys()]))  # 摄影地点

        pattern = re.compile(r"('[\u4e00-\u9fa5]+.[\u4e00-\u9fa5]+)|('[\u4e00-\u9fa5]+)")
        result = pattern.findall(str(keywords_list))
        # 提取所有中文，过滤掉编号，手机号，英文名等信息
        # result：  [("'乔治·多帕斯", ''), ('', "'大兴"), ('', "'荟聚"), ('', "'购物"), ('', "'商场"), ("'乔治·多帕斯", '')]
        result = [i for k in result for i in k]  # 展开列表
        result2 = [i.replace('\'', '') for i in result if len(i) > 1]  # ['乔治·多帕斯', '大兴', '荟聚', '购物', '商场', '乔治·多帕斯']
        print('seg结果：{}'.format(result2))
        d = {k: len(k) for k in result2}  # 将结果转化为字典
        # print('切词结果:{}'.format(d))
        d = {k: v for k, v in d.items() if k not in self.stop_words.keys() and len(
            k) > 1 and k not in nationality and k not in names}  # 去除停用词,过滤只有一个字的词汇和已经在国籍和姓名中出现的信息

        d_order = sorted(d.items(), key=lambda x: x[1], reverse=True)  # 关键词根据长度排序
        # 取前5个关键词，若关键词少于5个则取所有关键词
        top_n = 5 if len(d_order) > 5 else len(d_order)
        key_words = [s[0] for s in d_order[:top_n]]  # 取前5个关键字
        print('前{}个关键词:{}'.format(top_n, key_words))
        final_kew_words = []
        if len(key_words) > 0:
            # 去重，如关键词中为 ['爱国主义教育'， '爱国主义'] 舍弃重复的’爱国主义‘
            final_kew_words.append(key_words[0])  # 先将第一个元素添加进去
            for index in range(len(key_words) - 1, -1, -1):
                for j in key_words[:index]:
                    if key_words[index] not in j:  # 后面的元素在前面未出现过则添加
                        final_kew_words.append(key_words[index])
                        continue
                    else:  # 后面的元素在前面出现过就舍弃
                        break
            final_kew_words = list(set(final_kew_words))

        print("词性标注结果：{}".format(d_order))
        print("去重后的结果：{}".format(final_kew_words))
        return loc, final_kew_words, names, nationality

    # @timmer
    def get_keyWords_byLac(self, title, lac, names, loc):
        '''
        对name和loc不存在的情况，通过词性标注的方式获取这两者信息
        :param title: 需要处理的图片标题
        :param lac: lac模型
        :param names: 摄影师列表
        :param loc: 拍摄地列表
        :return:
        '''
        print("开始对信息进行词性标注以获取姓名和地点:{}".format(title))

        if len(names) == 0:
            keywords_list = lac.run(title)
            d = {k: v for k, *v in zip(*keywords_list)}  # 将结果转化为字典
            names = [i for i in d if d[i] == ['PER']]

        if len(loc) == 0:
            keywords_list = lac.run(title)
            d = {k: v for k, *v in zip(*keywords_list)}  # 将结果转化为字典
            print('词性标注结果：{}'.format(d))
            loc = [i for i in d if d[i] in [['LOC'], ['ORG']] and i not in self.countries.keys()]  # 摄影地点

        return loc, names

    def similar_filter(self, new_title):
        print('*' * 100)
        print('上一个标题：' + self.last_title)
        print('这一个标题：' + new_title)
        similar_value = difflib.SequenceMatcher(None, self.last_title, new_title).quick_ratio()
        print('本标题与上一标题相似度为：{}'.format(similar_value))
        if similar_value > 0.94:
            print('本标题与上一标题类似，不处理')
            result_output = []
            pic = {}
            print('上一次的处理结果：{}'.format(result_output))
            # 去除连字符
            line = new_title.replace('-', ' ').replace('+', ' ')
            number = line[-13::].strip('\n')  # 图片编号
            print('number：' + number)
            pic[number] = self.last_result[0][self.last_number]
            result_output.append(pic)
            self.last_number = number
            print('这一次的处理结果:{}'.format(result_output))
            self.last_result = result_output
            print('上一次的处理结果：{}'.format(result_output))
            return result_output
        else:
            return False

    def get_data(self, line, lac, seg):
        """
        读取照片标题集合的文件，进行处理
        :param line: 图片标题信息
        :return:result_output 返回每个标题提取出的信息列表
        """

        # 判断本次标题是否和上次标题相似
        new_title = line
        result_output = self.similar_filter(new_title)
        self.last_title = new_title
        if result_output:
            return result_output

        # 输出结果
        result_output = []
        # 定义字典存放每一个标题提取中的数据
        pic = {}
        # 获取年月日
        year, month, day = self.get_time(r'' + line[:-18:].replace('.', '-').replace(' ', ''))
        print('提取出的年月日：{}  {}  {}'.format(year, month, day))

        # 去除连字符
        line = line.replace('-', ' ').replace('+', ' ')
        number = line[-13::].strip('\n')  # 图片编号
        print('number：' + number)
        self.last_number = number
        # 将图片标题分割为列表，如['Z:', 'yuexun', '2018图编外拍 2', '炫彩世界收图-3124张', '周世杰-20181025炫彩世界开幕式', 'DSCF4066.JPG']
        title_list = line[:-15:].split('\\')
        # print('tltle_list:{}'.format(title_list))
        tag_1 = title_list[2]  # 一级标签，作品来源

        # 获取拍摄地、关键事件名、摄影师名、摄影师国籍

        loc, keyWords, name, nationality = self.get_keyWords_byseg(' '.join(title_list[3:]).replace('jpg', ''), seg)
        print('{} {} {} {}'.format(name, nationality, loc, keyWords))
        if len(name) == 0 or len(loc) == 0:
            loc, name = self.get_keyWords_byLac(' '.join(keyWords), lac, name, loc)  # 尝试将keywords当作标题传进去
            # loc, name = self.get_keyWords_byLac(' '.join(title_list[3:]).replace('jpg', ''), lac, name, loc)
        print('{} {} {} {}'.format(name, nationality, loc, keyWords))
        pic[number] = [tag_1, year, month, day, name, nationality, loc, keyWords]
        result_output.append(pic)

        self.last_result = result_output
        # print(pic)
        print('-' * 100)
        return result_output

    def write_to_file(self, result_output):
        with open(self.result_path, 'w', encoding='utf-8') as f:
            for pics in result_output[0]:
                for pic in pics:
                    for key, value in pic.items():
                        f.write('{}\t'.format(key))
                        for i in value:
                            f.write('{}\t'.format(i))
                        f.write('\n')

    def multiprocess(self, result_path):
        with open(self.listDirs, 'r', encoding='utf-8') as file:
            content = file.readlines()
        from multiprocessing.dummy import Pool as ThreadPool
        lac = LAC(mode='lac')
        result_output = []
        pool = ThreadPool()
        result_output.append(pool.map(self.get_data, content, lac))
        pool.close()
        pool.join()
        self.write_to_file(result_output)

    @timmer
    def singleprocess(self):
        with open(self.listDirs, 'r', encoding='utf-8') as file:
            content = file.readlines()
        result_output = []
        lac = LAC(mode='lac')
        seg = LAC(mode='seg')
        result_output = [self.get_data(line, lac, seg) for line in content]
        print(result_output)
        self.write_to_file([result_output])


if __name__ == '__main__':
    start_time = time.time()

    old = sys.stdout  # 将当前系统输出储存到一个临时变量中
    f = open('output.txt', 'w', encoding='utf-8')

    sys.stdout = f  # 输出重定向到文件

    Path = os.path.dirname(os.getcwd())
    dataPath = Path + os.sep + 'data'
    listDirs = os.path.join(dataPath, 'renommelog.txt')
    result = os.path.join(dataPath, 'result_test.txt')
    pic = pic_classify(listDirs, result)
    pic.singleprocess()  # 单进程，方便观察输出结果
    # pic.multiprocess(listDirs, result) #多进程模式

    sys.stdout = old  # 还原原系统输出
    f.close()

    end_time = time.time()

    run_time = round(end_time - start_time, 5)
    print('运行时间为：{}'.format(run_time))
