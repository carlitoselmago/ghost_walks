import pymysql.cursors

class db():

    marginpos=0.2

    def __init__(self):

        # Connect to the database
        self.conn = pymysql.connect(host='localhost',
                                    user='ghost',
                                    password='walks',
                                    database='ghostwalks',
                                    cursorclass=pymysql.cursors.DictCursor)
        self.cursor=self.conn.cursor()
    
    def insertPos(self,tagid,x,y):
        sql = "INSERT INTO `positions` (`tagname`, `x`,`y`) VALUES (%s, %s,%s)"
        self.cursor.execute(sql,(tagid,x,y))
        self.conn.commit()

    def getNormValue(self,x,y):
        #get total count
        sql = "SELECT COUNT(*) as count FROM positions;"
        self.cursor.execute(sql)
        result = self.cursor.fetchone()
        total=result["count"]
        #get specific area count
        sql = "SELECT COUNT(x) as count FROM positions WHERE x>"+str(x-self.marginpos)+" AND x<"+str(x+self.marginpos)+" AND y>"+str(y-self.marginpos)+" AND y<"+str(y+self.marginpos)+";"
        self.cursor.execute(sql)
        result = self.cursor.fetchone()
        local=result["count"]
        norm=(local/total)
        #print("total",total,"local",local)
       
        return norm